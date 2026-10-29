import serial,time
from pathlib import Path
p=Path(r'D:\TrustGate-IoT\results\esp32-hardware.log')
s=serial.Serial('COM8',115200,timeout=0.5)
s.dtr=False
s.rts=False
end=time.monotonic()+65
ready=False
last_sent=0
with p.open('a') as f:
 f.write('\n--- New hardware test session ---\n'); f.flush()
 while time.monotonic()<end:
  if not ready and time.monotonic()-last_sent>3:
   s.write(('TIME '+str(int(time.time()))+'\n').encode());last_sent=time.monotonic()
  line=s.readline().decode(errors='replace')
  if line:
   if 'Time provisioned' in line: ready=True
   print(line,end='',flush=True); f.write(line); f.flush()
s.close()