const { execSync } = require('child_process');
const fs = require('fs');

console.log('🏎️  Setting up GT3 AI Coaching development environment...\n');

try {
  // Check Node.js version
  const nodeVersion = process.version;
  console.log(`📋 Node.js version: ${nodeVersion}`);
  
  if (parseInt(nodeVersion.slice(1)) < 16) {
    throw new Error('Node.js v16 or higher required');
  }

  // Install dependencies
  console.log('📦 Installing dependencies...');
  execSync('npm install', { stdio: 'inherit' });
  
  // Check for electron-builder
  try {
    execSync('npx electron-builder --version', { stdio: 'pipe' });
    console.log('✅ electron-builder ready');
  } catch (e) {
    console.log('🔧 Installing electron-builder...');
    execSync('npm install -g electron-builder', { stdio: 'inherit' });
  }
  
  console.log('\n✅ Development environment ready!');
  console.log('\n🎯 Next steps:');
  console.log('1. npm run dev - Start development mode');
  console.log('2. npm run build-installer - Create Windows installer');
  console.log('3. Start iRacing and join GT3 session');
  console.log('4. Press F10 to show overlay');
  
} catch (error) {
  console.error('\n❌ Setup failed:', error.message);
  console.error('\n🔧 Try:');
  console.error('1. Ensure Node.js v16+ is installed');
  console.error('2. Run as administrator if permission issues');
  console.error('3. Check internet connection for npm packages');
}
