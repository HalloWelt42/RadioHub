#!/bin/bash
# Download Roboto, Orbitron & Share Tech Mono WOFF2 Fonts
# Wird beim Docker Build ausgeführt

FONTS_DIR="src/styles/fonts"
mkdir -p $FONTS_DIR

echo "Downloading fonts from Google Fonts..."

# Orbitron Variable Font (enthält alle Gewichte 400-900)
# URL von fonts.googleapis.com CSS
echo "Downloading Orbitron..."
curl -sL "https://fonts.gstatic.com/s/orbitron/v35/yMJRMIlzdpvBhQQL_Qq7dy0.woff2" \
  -o "$FONTS_DIR/orbitron.woff2" 2>/dev/null

if [ -f "$FONTS_DIR/orbitron.woff2" ] && [ -s "$FONTS_DIR/orbitron.woff2" ]; then
  echo "✓ Orbitron font downloaded"
else
  echo "✗ Failed to download Orbitron"
fi

# Roboto in verschiedenen Gewichten
echo "Downloading Roboto fonts..."

# Roboto 300 (Light)
curl -sL "https://fonts.gstatic.com/s/roboto/v30/KFOlCnqEu92Fr1MmSU5fBBc4.woff2" \
  -o "$FONTS_DIR/roboto-300.woff2" 2>/dev/null
[ -s "$FONTS_DIR/roboto-300.woff2" ] && echo "✓ Roboto 300" || echo "✗ Roboto 300"

# Roboto 400 (Regular)
curl -sL "https://fonts.gstatic.com/s/roboto/v30/KFOmCnqEu92Fr1Mu4mxK.woff2" \
  -o "$FONTS_DIR/roboto-400.woff2" 2>/dev/null
[ -s "$FONTS_DIR/roboto-400.woff2" ] && echo "✓ Roboto 400" || echo "✗ Roboto 400"

# Roboto 500 (Medium)
curl -sL "https://fonts.gstatic.com/s/roboto/v30/KFOlCnqEu92Fr1MmEU9fBBc4.woff2" \
  -o "$FONTS_DIR/roboto-500.woff2" 2>/dev/null
[ -s "$FONTS_DIR/roboto-500.woff2" ] && echo "✓ Roboto 500" || echo "✗ Roboto 500"

# Roboto 700 (Bold)
curl -sL "https://fonts.gstatic.com/s/roboto/v30/KFOlCnqEu92Fr1MmWUlfBBc4.woff2" \
  -o "$FONTS_DIR/roboto-700.woff2" 2>/dev/null
[ -s "$FONTS_DIR/roboto-700.woff2" ] && echo "✓ Roboto 700" || echo "✗ Roboto 700"

# Roboto 900 (Black)
curl -sL "https://fonts.gstatic.com/s/roboto/v30/KFOlCnqEu92Fr1MmYUtfBBc4.woff2" \
  -o "$FONTS_DIR/roboto-900.woff2" 2>/dev/null
[ -s "$FONTS_DIR/roboto-900.woff2" ] && echo "✓ Roboto 900" || echo "✗ Roboto 900"

# Share Tech Mono - latin
echo "Downloading Share Tech Mono..."
curl -sL "https://fonts.gstatic.com/s/sharetechmono/v15/J7aHnp1uDWRBEqV98dVQztYldFcLowEF.woff2" \
  -o "$FONTS_DIR/share-tech-mono.woff2" 2>/dev/null

if [ -f "$FONTS_DIR/share-tech-mono.woff2" ] && [ -s "$FONTS_DIR/share-tech-mono.woff2" ]; then
  echo "✓ Share Tech Mono font downloaded"
else
  echo "✗ Failed to download Share Tech Mono"
fi

echo ""
echo "Font download complete!"
echo "Files in fonts directory:"
ls -la $FONTS_DIR
