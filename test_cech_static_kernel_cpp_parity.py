import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import hgraph_cech_static_kernel as k


class CechCppPythonParityTests(unittest.TestCase):
    def test_cpp_python_parity_and_deterministic_replay(self):
        compiler = shutil.which("g++")
        self.assertIsNotNone(compiler, "g++ is required for C++ parity")
        source = Path("hgraph_cech_static_kernel.cpp")
        self.assertTrue(source.exists(), "C++ kernel source is missing")

        python_first = k.cpp_parity_summary()
        python_second = k.cpp_parity_summary()
        self.assertEqual(python_first, python_second)

        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "eq64_cech_cpp"
            subprocess.run(
                [compiler, "-std=c++17", "-O2", "-DEQ64_CECH_STANDALONE", str(source), "-o", str(binary)],
                check=True, capture_output=True, text=True,
            )
            cpp_first = subprocess.run([str(binary)], check=True, capture_output=True, text=True, timeout=30).stdout
            cpp_second = subprocess.run([str(binary)], check=True, capture_output=True, text=True, timeout=30).stdout
            self_first = subprocess.run([str(binary), "--selfcheck"], check=True, capture_output=True, text=True, timeout=30).stdout
            self_second = subprocess.run([str(binary), "--selfcheck"], check=True, capture_output=True, text=True, timeout=30).stdout

        self.assertEqual(cpp_first, cpp_second)
        self.assertEqual(cpp_first, python_first)
        self.assertEqual(self_first, self_second)
        self.assertEqual(
            self_first,
            "DELTA2_ALL=1\nHOMOTOPY_ALL=1\nH0_REDUCED_ALL=1\nMUTANT_DETECTED=1\n",
        )


if __name__ == "__main__":
    unittest.main()
