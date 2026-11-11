# Zed component checks and build observations

Source: `zedlanguage/zed` at `4598c420ab65fba1942f12a0888bc9f638fba9f9`. Host: macOS/ARM64. Toolchain: installed Rust 1.99, selected through `rustup run 1.99`. No upstream source changes were made.

From a checkout of that revision:

```sh
RUSTFLAGS='-C linker=/usr/bin/clang' rustup run 1.99 cargo test --locked -p zed-kernel --lib bits::tests -- --nocapture
RUSTFLAGS='-C linker=/usr/bin/clang' rustup run 1.99 cargo build --release --locked -p zed-native --bin zedc
```

Three kernel tests passed. The native compiler build failed on Linux-specific runtime APIs. An initial attempt using the host's older default nightly toolchain also encountered a dylib linker error; switching toolchain and C linker exposed the platform errors recorded in [results.json](results.json).

To isolate the interpreter, a separate temporary Cargo package depended on `crates/zedc` by absolute path and used this `src/main.rs`:

```rust
fn main() {
    let args = std::env::args_os().skip(1).collect::<Vec<_>>();
    let (mut input, mut output, mut error) =
        (std::io::stdin(), std::io::stdout(), std::io::stderr());
    std::process::exit(
        zedc::run::command(&args, &mut input, &mut output, &mut error).into()
    );
}
```

This also failed on macOS because `place.rs` uses `OFlags::PATH`. No end-to-end Zed program or timing comparison completed. The observations do not assess Linux build success or the full upstream test suite.
