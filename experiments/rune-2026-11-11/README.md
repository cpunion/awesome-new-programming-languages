# Rune behavior probes

The six probes in [run.py](run.py) target Rune commit `a8fb12f974736f20eaefb1f614df68411dac7bc8`. [results.json](results.json) records **five expected outcomes and one discrepancy**: the compiler accepts a conditional branch on a secret derived from a command-line argument. The script deliberately exits with status 1 when that documented restriction is not enforced. The result includes the emitted function's LLVM IR and a successful run with argument `password`.

The other probes check secret indexing, type changes, bounds, overflow, and generated doubly linked relationship methods. Bounds failure prints a panic and exits with status 139 in the tested environment. No upstream test-suite pass or performance measurement is claimed.

## Build used

Host: Apple M4 Max, macOS. Container: Ubuntu 24.04 **x86-64**, running through the host's container environment. Ubuntu image ID: `sha256:d9b8c34d61a9b9a3c44cab883d7d2f2619d674966ab520186f799cf32e3e0377`. These conditions are suitable for behavior checks; no timing comparison with host-native compilers is made.

Checked-out dependencies:

- Rune: `a8fb12f974736f20eaefb1f614df68411dac7bc8`
- DataDraw: `a2491e6247c34d06c6cc46e353ebc6a59d031dd3`
- CTTK: `1d592024398f06c8eda1d325bdbd105ac32d92b3`

Arrange the three checkouts as siblings named `rune`, `datadraw`, and `CTTK`. Mount their parent at `/work` in a disposable Ubuntu container. Install dependencies there:

```sh
apt-get update
apt-get install -y --no-install-recommends automake autoconf libtool bison build-essential clang-14 flex libgmp-dev ca-certificates
ln -s /usr/bin/clang-14 /usr/local/bin/clang
cd /work/datadraw
./autogen.sh
./configure
make -j4
make install
cp /work/CTTK/inc/cttk.h /work/CTTK
cd /work/rune
make -j4 rune
```

The `clang` symlink supplies the command expected by the runtime Makefile and driver. The compiler and runtime use the upstream default Makefiles, including their debug flags; each probe's generated program is compiled with Rune `-O`, with safety checks enabled. No upstream tracked source was changed. These commands adapt the upstream Linux build instructions to Ubuntu 24.04; they do not install tools on the host.

Keep that container running, then from this repository on the host:

```sh
python3 experiments/rune-2026-11-11/run.py --source /path/to/rune --container CONTAINER_NAME
```

For a native Linux build, omit `--container`. The script writes temporary probe files beside the source checkout, so the parent directory must be writable. A status of 1 is the expected recorded result for this snapshot's secret-branch discrepancy; inspect the JSON rather than treating that status as an infrastructure failure.
