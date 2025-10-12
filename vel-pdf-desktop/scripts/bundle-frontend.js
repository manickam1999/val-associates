const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const rootDir = path.join(__dirname, '..', '..');
const frontendSrcDir = path.join(rootDir, 'vel-pdf-web');
const frontendDestDir = path.join(__dirname, '..', 'resources', 'frontend');

console.log('Starting frontend bundling...');
console.log('Source:', frontendSrcDir);
console.log('Destination:', frontendDestDir);

// Create destination directory
if (!fs.existsSync(frontendDestDir)) {
  fs.mkdirSync(frontendDestDir, { recursive: true });
}

try {
  // Build Next.js in standalone mode
  console.log('\n1. Building Next.js application...');
  execSync('npm run build', {
    cwd: frontendSrcDir,
    stdio: 'inherit'
  });

  console.log('\n2. Copying standalone output...');

  const standaloneDir = path.join(frontendSrcDir, '.next', 'standalone');
  const staticDir = path.join(frontendSrcDir, '.next', 'static');
  const publicDir = path.join(frontendSrcDir, 'public');

  // Copy recursive function
  const copyRecursive = (src, dest) => {
    if (!fs.existsSync(src)) {
      console.warn(`Warning: ${src} does not exist, skipping...`);
      return;
    }

    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }

    const entries = fs.readdirSync(src, { withFileTypes: true });

    for (const entry of entries) {
      const srcPath = path.join(src, entry.name);
      const destPath = path.join(dest, entry.name);

      if (entry.isDirectory()) {
        copyRecursive(srcPath, destPath);
      } else {
        fs.copyFileSync(srcPath, destPath);
      }
    }
  };

  // Copy standalone files
  copyRecursive(standaloneDir, frontendDestDir);

  // Copy static files
  const destStaticDir = path.join(frontendDestDir, '.next', 'static');
  copyRecursive(staticDir, destStaticDir);

  // Copy public files
  const destPublicDir = path.join(frontendDestDir, 'public');
  copyRecursive(publicDir, destPublicDir);

  console.log('\n3. Frontend bundled successfully!');
  console.log(`Output directory: ${frontendDestDir}`);

  // For Windows, we'll need to bundle Node.js runtime
  if (process.platform === 'win32') {
    console.log('\n4. Note: For Windows distribution, Node.js runtime will be bundled by electron-builder.');
  }

} catch (error) {
  console.error('Error bundling frontend:', error.message);
  process.exit(1);
}
