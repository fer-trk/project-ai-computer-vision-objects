"""Check temporal integrity, streaming exports and failures with real tiny videos."""
import csv,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from predict_video import run_video,annotate_frame
from inspect_video import VideoError
from predict_image import PredictionError,file_hash
from PIL import Image

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
class VideoPredictionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.video=self.root/'source.mp4';self.weights=self.root/'fixture.pt';self.weights.write_bytes(b'controlled test; not a model')
  self.output=self.root/'result';self.make_video()
 def make_video(self,filter_value=None):
  cmd=['ffmpeg','-y','-v','error','-f','lavfi','-i','testsrc2=size=320x240:rate=10:duration=1']
  if filter_value:cmd+=['-vf',filter_value,'-fps_mode','vfr']
  subprocess.run(cmd+['-c:v','mpeg4','-q:v','2',str(self.video)],check=True,capture_output=True)
 def predict(self,image):return {0:'nox_texto'},[dict(bbox_xyxy=[20,30,90,60],class_id=0,confidence=.8)]
 def run_video(self,**kw):return run_video(self.video,self.weights,self.output,confidence=.25,predictor=kw.pop('predictor',self.predict),**kw)
 def test_complete_video_and_exports_match_every_source_frame(self):
  before=file_hash(self.video);r=self.run_video();self.assertTrue(r['complete']);self.assertEqual(r['frames_processed'],10)
  self.assertEqual(r['detection_count'],10);self.assertEqual(r['output']['verified_frames'],10)
  self.assertEqual(file_hash(self.video),before);self.assertEqual(r['model']['sha256'],file_hash(self.weights))
  lines=[json.loads(l) for l in (self.output/'frames.jsonl').read_text().splitlines()]
  with (self.output/'detections.csv').open(newline='') as f:rows=list(csv.DictReader(f))
  self.assertEqual(len(lines),len(rows));self.assertEqual(lines[0]['detections'][0]['evidence_status'],'unreviewed')
  self.assertEqual(float(rows[-1]['timestamp_seconds']),.9)
 def test_vfr_and_nonzero_origin_preserve_relative_times(self):
  self.make_video("select='not(eq(n,3)+eq(n,4))',setpts=PTS+2/TB")
  r=self.run_video();lines=[json.loads(l) for l in (self.output/'frames.jsonl').read_text().splitlines()]
  self.assertEqual([round(l['timestamp_seconds'],1) for l in lines],[0,.1,.2,.5,.6,.7,.8,.9])
  self.assertAlmostEqual(lines[0]['source_pts_seconds'],2);self.assertEqual(r['frames_processed'],8)
  self.assertAlmostEqual(lines[2]['duration_seconds'],.3)
 def test_no_detections_is_valid_with_csv_header_and_frames(self):
  r=self.run_video(predictor=lambda image:({0:'nox_texto'},[]))
  self.assertEqual(r['detection_count'],0);self.assertEqual(len((self.output/'detections.csv').read_text().splitlines()),1)
  self.assertFalse((self.output/'first-detection.png').exists())
 def test_existing_output_not_overwritten(self):
  self.output.mkdir();(self.output/'keep').write_text('keep')
  with self.assertRaises(FileExistsError):self.run_video()
  self.assertEqual((self.output/'keep').read_text(),'keep')
 def test_detector_failure_does_not_publish_partial_results(self):
  calls=0
  def fail(image):
   nonlocal calls
   calls+=1
   if calls==3:raise RuntimeError('controlled failure')
   return self.predict(image)
  with self.assertRaises(RuntimeError):self.run_video(predictor=fail)
  self.assertFalse(self.output.exists());self.assertFalse(list(self.root.glob('.video-*')))
 def test_invalid_class_or_low_score_rejected(self):
  for names,score in [({0:'other_brand'},.9),({0:'nox_texto'},.1)]:
   with self.subTest(names=names,score=score),self.assertRaises(PredictionError):
    self.run_video(predictor=lambda image:(names,[dict(bbox_xyxy=[1,1,20,20],class_id=0,confidence=score)]))
   self.assertFalse(self.output.exists())
 def test_limits_invalid_video_and_options_fail_without_results(self):
  for kw in [dict(max_duration_seconds=.1),dict(max_pixels=10),dict(image_size=33)]:
   with self.subTest(kw=kw),self.assertRaises(ValueError):self.run_video(**kw)
   self.assertFalse(self.output.exists())
  self.video.write_text('invalid')
  with self.assertRaises(VideoError):self.run_video()
 def test_render_places_label_below_box_on_fixed_canvas(self):
  image=Image.new('RGB',(320,240),'white')
  d=dict(detection_id=1,bbox_xyxy=[20,30,90,60],confidence=.8)
  out=annotate_frame(image,[d],.1)
  self.assertEqual(out.size,(320,352));self.assertEqual(out.getpixel((20,78)),(255,179,71))
  self.assertNotEqual(out.getpixel((23,113)),(255,255,255))
if __name__=='__main__':unittest.main()
