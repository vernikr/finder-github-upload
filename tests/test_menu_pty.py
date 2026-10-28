import os, pty, select, subprocess, sys, time, unittest

class MenuTests(unittest.TestCase):
    def test_arrow_down_and_enter(self):
        master, slave = pty.openpty()
        process = subprocess.Popen([sys.executable, '-c', "import upload; print('SELECTED=',upload.choose('Choose',['First','Second']))"], stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        data=b''
        try:
            deadline=time.monotonic()+5
            while b'Second' not in data and time.monotonic()<deadline:
                if select.select([master],[],[],0.2)[0]: data+=os.read(master,4096)
            self.assertIn(b'Second',data)
            os.write(master,b'\x1b[B\r')
            while process.poll() is None and time.monotonic()<deadline:
                if select.select([master],[],[],0.2)[0]:
                    try: data+=os.read(master,4096)
                    except OSError: break
            process.wait(timeout=2)
            try:
                while select.select([master],[],[],0)[0]: data+=os.read(master,4096)
            except OSError: pass
            self.assertIn(b'SELECTED= 1',data)
        finally:
            if process.poll() is None: process.kill();process.wait()
            os.close(master)
