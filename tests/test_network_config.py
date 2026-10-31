import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('configure',Path(__file__).resolve().parents[1]/'scripts/configure-network.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class NetworkConfigTests(unittest.TestCase):
    def test_update_preserves_credentials_and_loopback(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            config=root/'client/esp32/include/config.h';config.parent.mkdir(parents=True)
            config.write_text('#define TG_GATEWAY_IP "192.168.1.3"\n#define TG_WIFI_PASSWORD "test-only"\n')
            gateway=root/'gateway/unbound.conf';gateway.parent.mkdir()
            gateway.write_text('server:\n    interface: 127.0.0.1\n    interface: 172.25.1.2@1853\n    access-control: 127.0.0.0/8 allow\n    access-control: 192.168.1.4/32 allow\n')
            with contextlib.redirect_stdout(io.StringIO()) as output:
                module.update(root,'192.168.1.8','172.25.1.2','192.168.1.9','172.25.0.0/20')
            self.assertIn('"test-only"',config.read_text())
            self.assertNotIn('test-only',output.getvalue())
            self.assertIn('interface: 127.0.0.1\n',gateway.read_text())
            self.assertIn('192.168.1.9/32 allow',gateway.read_text())
            self.assertNotIn('192.168.1.4',gateway.read_text())

    def test_invalid_wsl_subnet_rejected_before_writes(self):
        with self.assertRaises(ValueError):
            module.update(Path('/nonexistent'),'192.168.1.8','172.25.1.2','192.168.1.9','10.0.0.0/24')


if __name__=='__main__': unittest.main()
