#!/bin/bash

echo "🔧 Setting up legacy Rust (1.22.1) environment for actix-http..."

# Set Rust 1.22.1 for this project
rustup install 1.22.1
echo "1.22.1" > rust-toolchain
rustup override set 1.22.1

# Install components needed for IDE support
rustup component add rust-src --toolchain 1.22.1
rustup component add rls --toolchain 1.22.1
rustup component add rust-analysis --toolchain 1.22.1

# Create VSCode settings to avoid rust-analyzer errors
mkdir -p .vscode
cat <<EOF > .vscode/settings.json
{
  "rust-analyzer.cargo.buildScripts.enable": false,
  "rust-analyzer.checkOnSave.enable": false,
  "rust-client.engine": "rls"
}
EOF

echo "✅ Legacy environment setup complete. Rust 1.22.1 is now active in this project."
