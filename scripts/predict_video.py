"""Annotate every video frame with a fixed local NOX checkpoint and source times."""
import argparse
from contextlib import redirect_stdout
import csv
from datetime import datetime, timezone
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time

import av
import cv2
from PIL import Image, ImageDraw, ImageFont

from inspect_video import VideoError, open_video
from predict_image import PredictionError, file_hash, normalize_detections, package_versions, probability


class LocalDetector:
    """Load the selected checkpoint once, without replacing it with a download."""
    def __init__(self, checkpoint, confidence, iou, image_size):
        os.environ.setdefault('YOLO_CONFIG_DIR', str(Path(__file__).resolve().parents[1]/'local-artifacts/ultralytics'))
        os.environ.setdefault('YOLO_OFFLINE', 'true')
        from ultralytics import YOLO
        self.model=YOLO(str(checkpoint), task='detect')
        self.options=dict(device='cpu',conf=confidence,iou=iou,imgsz=image_size,max_det=300,save=False,verbose=False)
        if self.model.task!='detect' or self.model.names!={0:'nox_texto'}:
            raise PredictionError('Se requiere el checkpoint de detección de una clase nox_texto')

    def __call__(self, image):
        result=self.model.predict(source=image,**self.options)[0]
        boxes=[dict(bbox_xyxy=xyxy,class_id=label,confidence=score) for xyxy,label,score in zip(
            result.boxes.xyxy.cpu().tolist(),result.boxes.cls.cpu().tolist(),result.boxes.conf.cpu().tolist(),strict=True)]
        return dict(self.model.names),boxes


def annotate_frame(image, detections, timestamp):
    """Keep fixed encoder dimensions; put each label underneath its source box."""
    width,height=image.size
    canvas=Image.new('RGB',((width+1)//2*2,(height+113)//2*2),'#17202b')
    canvas.paste(image,(0,48))
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.load_default(size=max(10,min(22,width//45)))
    notice='NOX experimental | revisar | sin medicion de exposicion'
    draw.text((6,4),notice,font=font,fill='white')
    draw.text((6,25),f't={timestamp:.3f}s | {len(detections)} propuestas',font=font,fill='white')
    for d in detections:
        x1,y1,x2,y2=d['bbox_xyxy']
        draw.rectangle((x1,y1+48,x2,y2+48),outline='#ffb347',width=3)
        text=f"{d['detection_id']}: NOX {100*d['confidence']:.1f}% [revisar]"
        text_width=draw.textlength(text,font=font)
        left=max(0,min(x1,width-text_width-6))
        top=y2+50
        draw.rectangle((left,top,left+text_width+6,top+font.size+6),fill='#17202b')
        draw.text((left+3,top+2),text,font=font,fill='#ffcf87')
    return canvas


def timed_frames(frames, info):
    """Use one-frame lookahead to preserve variable frame intervals."""
    current=next(frames,None)
    if current is None:raise VideoError('No se decodificaron fotogramas')
    for following in frames:
        yield current,following.timestamp_seconds-current.timestamp_seconds
        current=following
    duration=info['duration_seconds']-current.timestamp_seconds
    if not math.isfinite(duration) or duration<=0:
        raise VideoError('La duración declarada no cubre el último fotograma')
    yield current,duration


def verify_output(path, frame_log):
    """Reopen the encoded video and compare every timestamp with the saved source log."""
    count=0
    with av.open(str(path)) as container, Path(frame_log).open(encoding='utf-8') as lines:
        for decoded in container.decode(video=0):
            line=lines.readline()
            if not line:raise VideoError('El vídeo generado contiene fotogramas adicionales')
            expected=json.loads(line)
            if abs(float(decoded.pts*decoded.time_base)-expected['timestamp_seconds'])>0.00001:
                raise VideoError('El vídeo generado no conserva los timestamps')
            count+=1
        if lines.readline():raise VideoError('Faltan fotogramas en el vídeo generado')
    return count


def run_video(video, checkpoint, output, *, confidence, iou=.7, image_size=640,
              max_duration_seconds=None, max_pixels=None, predictor=None):
    """Stream inference and JSONL, publishing only complete verified results."""
    video,checkpoint,output=(Path(p).resolve() for p in (video,checkpoint,output))
    confidence=probability(confidence,'Confianza');iou=probability(iou,'IoU de supresión')
    if isinstance(image_size,bool) or not isinstance(image_size,int) or image_size<32 or image_size%32:
        raise PredictionError('imgsz debe ser un entero múltiplo de 32')
    if not checkpoint.is_file() or checkpoint.suffix.lower()!='.pt':
        raise PredictionError('Indica un checkpoint .pt local existente')
    if output.exists():raise FileExistsError('La carpeta de salida ya existe')
    if output in video.parents or output in checkpoint.parents:
        raise PredictionError('La salida no puede contener las entradas')
    if not video.is_file():raise VideoError('No existe el vídeo')
    hashes=dict(video=file_hash(video),checkpoint=file_hash(checkpoint))
    start=time.perf_counter();inference_seconds=0.0
    count=total=with_detections=0;names=None
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.video-',dir=output.parent) as temporary:
        staged=Path(temporary)/'result';staged.mkdir()
        with open_video(video,max_duration_seconds=max_duration_seconds,max_pixels=max_pixels) as (info,frames):
            with redirect_stdout(sys.stderr):
                detector=predictor or LocalDetector(checkpoint,confidence,iou,image_size)
            fields=['frame_index','source_pts_seconds','timestamp_seconds','detection_id','class_id','class_name','confidence','x1','y1','x2','y2','evidence_status','support']
            time_base=Fraction(1,1_000_000)
            with (staged/'frames.jsonl').open('w',encoding='utf-8') as log, (staged/'detections.csv').open('w',encoding='utf-8',newline='') as table, av.open(str(staged/'annotated.mp4'),'w') as encoded:
                writer=csv.DictWriter(table,fieldnames=fields);writer.writeheader()
                rate=Fraction(info['average_frame_rate'])
                if rate<=0:raise VideoError('Frecuencia nominal no válida')
                stream=encoded.add_stream('libx264',rate=rate)
                stream.width=(info['width']+1)//2*2;stream.height=(info['height']+113)//2*2
                stream.pix_fmt='yuv420p';stream.time_base=time_base;stream.codec_context.time_base=time_base
                stream.options={'preset':'ultrafast','crf':'23','tune':'zerolatency','bf':'0'}
                durations={}
                def mux(packets):
                    for packet in packets:
                        key=round(float(packet.pts*packet.time_base)/float(time_base))
                        duration=durations.pop(key,None)
                        if duration is None:raise VideoError('El codificador devolvió un timestamp desconocido')
                        packet.duration=max(1,round(duration/float(packet.time_base)))
                        encoded.mux(packet)
                for frame,duration in timed_frames(frames,info):
                    image=Image.fromarray(cv2.cvtColor(frame.image,cv2.COLOR_BGR2RGB))
                    tick=time.perf_counter()
                    with redirect_stdout(sys.stderr):predicted_names,boxes=detector(image)
                    inference_seconds+=time.perf_counter()-tick
                    current_names,detections=normalize_detections(predicted_names,boxes,image.size)
                    if current_names!={0:'nox_texto'}:raise PredictionError('Solo se admite texto NOX')
                    if names is not None and names!=current_names:raise PredictionError('Las clases cambiaron entre frames')
                    names=current_names
                    if any(d['confidence']+1e-8<confidence for d in detections):
                        raise PredictionError('El predictor devolvió scores inferiores al umbral')
                    entry=dict(frame_index=frame.index,source_pts_seconds=frame.source_pts_seconds,
                        timestamp_seconds=frame.timestamp_seconds,duration_seconds=duration,detections=detections)
                    log.write(json.dumps(entry,ensure_ascii=False,allow_nan=False)+'\n')
                    for d in detections:
                        writer.writerow(dict(frame_index=frame.index,source_pts_seconds=frame.source_pts_seconds,
                            timestamp_seconds=frame.timestamp_seconds,**{k:d[k] for k in ('detection_id','class_id','class_name','confidence','evidence_status','support')},
                            **dict(zip(('x1','y1','x2','y2'),d['bbox_xyxy'],strict=True))))
                    canvas=annotate_frame(image,detections,frame.timestamp_seconds)
                    if count==0:canvas.save(staged/'preview.png')
                    if detections and with_detections==0:canvas.save(staged/'first-detection.png')
                    pixel_frame=av.VideoFrame.from_image(canvas);pixel_frame.pts=round(frame.timestamp_seconds/float(time_base));pixel_frame.time_base=time_base
                    durations[pixel_frame.pts]=duration;mux(stream.encode(pixel_frame))
                    count+=1;total+=len(detections);with_detections+=bool(detections)
                    last_timestamp=frame.timestamp_seconds;last_duration=duration
                mux(stream.encode())
                if durations:raise VideoError('El codificador dejó fotogramas sin publicar')
        verified=verify_output(staged/'annotated.mp4',staged/'frames.jsonl')
        if verified!=count:raise VideoError('El conteo de salida no coincide')
        report=dict(schema_version=1,created_utc=datetime.now(timezone.utc).isoformat(),complete=True,
            experimental=True,model_accepted=False,source=dict(name=video.name,sha256=hashes['video'],**info),
            model=dict(name=checkpoint.name,sha256=hashes['checkpoint'],names=names),
            parameters=dict(confidence=confidence,nms_iou=iou,image_size=image_size,device='cpu',frame_stride=1,
                max_duration_seconds=max_duration_seconds,max_pixels=max_pixels),
            frames_processed=count,frames_with_detections=with_detections,detection_count=total,
            last_timestamp_seconds=last_timestamp,last_interval_seconds=last_duration,
            inference_seconds=inference_seconds,elapsed_seconds=time.perf_counter()-start,
            output=dict(video='annotated.mp4',audio=False,frames='frames.jsonl',detections='detections.csv',
                timing='Source-relative PTS; VFR retained within 10 microseconds',verified_frames=verified),
            exposure_measurement='not_computed; detections unreviewed, support unknown',
            versions=dict(package_versions(),av=av.__version__))
        (staged/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
        staged.rename(output)
    return report


def main():
    p=argparse.ArgumentParser(description='Generar vídeo NOX experimental con cajas y timestamps')
    p.add_argument('video',type=Path);p.add_argument('--model',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--confidence',type=float,required=True)
    p.add_argument('--iou',type=float,default=.7);p.add_argument('--imgsz',type=int,default=640)
    p.add_argument('--max-duration-seconds',type=float);p.add_argument('--max-pixels',type=int)
    a=p.parse_args()
    try:
        report=run_video(a.video,a.model,a.output,confidence=a.confidence,iou=a.iou,image_size=a.imgsz,
            max_duration_seconds=a.max_duration_seconds,max_pixels=a.max_pixels)
    except (ValueError,OSError,RuntimeError) as e:p.exit(2,f'Error de análisis: {e}\n')
    print(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False))

if __name__=='__main__':main()
