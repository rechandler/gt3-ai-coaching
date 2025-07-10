// build-all.js - Automated build script for GT3 AI Coaching with Python telemetry

const { exec, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const util = require('util');

const execAsync = util.promisify(exec);

class GT3Builder {
    constructor() {
        this.projectRoot = process.cwd();
        this.pythonServerDir = path.join(this.projectRoot, 'python-server');
        this.buildDir = path.join(this.projectRoot, 'build');
        this.distDir = path.join(this.projectRoot, 'dist');
    }

    async log(message) {
        console.log(`[GT3 Builder] ${message}`);
    }

    async checkDependencies() {
        this.log('Checking build dependencies...');
        
        try {
            // Check Python
            const pythonVersion = await execAsync('python --version');
            this.log(`✅ Python: ${pythonVersion.stdout.trim()}`);
        } catch (e) {
            try {
                const pythonVersion = await execAsync('py --version');
                this.log(`✅ Python: ${pythonVersion.stdout.trim()}`);
            } catch (e2) {
                throw new Error('❌ Python not found. Please install Python 3.8+');
            }
        }

        try {
            // Check PyInstaller
            await execAsync('pyinstaller --version');
            this.log('✅ PyInstaller found');
        } catch (e) {
            this.log('Installing PyInstaller...');
            await execAsync('pip install pyinstaller');
            this.log('✅ PyInstaller installed');
        }

        try {
            // Check Node dependencies
            const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
            this.log(`✅ Project: ${packageJson.name} v${packageJson.version}`);
        } catch (e) {
            throw new Error('❌ package.json not found');
        }

        this.log('All dependencies check passed!');
    }

    async buildPythonServer() {
        this.log('Building Python telemetry server...');
        
        // Ensure python-server directory exists
        if (!fs.existsSync(this.pythonServerDir)) {
            fs.mkdirSync(this.pythonServerDir, { recursive: true });
        }

        // Create requirements.txt if it doesn't exist
        const requirementsPath = path.join(this.pythonServerDir, 'requirements.txt');
        if (!fs.existsSync(requirementsPath)) {
            const requirements = `irsdk>=1.0.0
websockets>=11.0.0
asyncio`;
            fs.writeFileSync(requirementsPath, requirements);
            this.log('Created requirements.txt');
        }

        // Install Python dependencies
        this.log('Installing Python dependencies...');
        await execAsync('pip install -r requirements.txt', { 
            cwd: this.pythonServerDir 
        });

        // Create PyInstaller spec if it doesn't exist
        const specPath = path.join(this.pythonServerDir, 'telemetry-server.spec');
        if (!fs.existsSync(specPath)) {
            const specContent = `# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['telemetry-server.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['irsdk', 'websockets', 'asyncio', 'json', 'logging'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='gt3-telemetry-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)`;
            fs.writeFileSync(specPath, specContent);
            this.log('Created PyInstaller spec file');
        }

        // Build Python executable
        this.log('Creating Python executable...');
        await execAsync('pyinstaller telemetry-server.spec --clean', { 
            cwd: this.pythonServerDir 
        });

        const exePath = path.join(this.pythonServerDir, 'dist', 'gt3-telemetry-server.exe');
        if (fs.existsSync(exePath)) {
            this.log('✅ Python telemetry server built successfully');
            return exePath;
        } else {
            throw new Error('❌ Failed to build Python executable');
        }
    }

    async buildElectronApp() {
        this.log('Building Electron application...');

        // Install Node dependencies
        this.log('Installing Node.js dependencies...');
        await execAsync('npm install');

        // Build Electron app
        this.log('Building Electron app...');
        await execAsync('npm run build');

        this.log('✅ Electron application built successfully');
    }

    async createInstaller() {
        this.log('Creating Windows installer...');

        // Copy Python executable to resources
        const pythonExe = path.join(this.pythonServerDir, 'dist', 'gt3-telemetry-server.exe');
        const resourcesDir = path.join(this.buildDir, 'resources');
        
        if (!fs.existsSync(resourcesDir)) {
            fs.mkdirSync(resourcesDir, { recursive: true });
        }

        fs.copyFileSync(pythonExe, path.join(resourcesDir, 'gt3-telemetry-server.exe'));
        this.log('Copied Python server to resources');

        // Create NSIS installer
        try {
            await execAsync('makensis installer/gt3-installer.nsi');
            this.log('✅ Windows installer created successfully');
        } catch (e) {
            this.log('⚠️  NSIS not found, using electron-builder instead');
            await execAsync('npm run build');
        }
    }

    async testBuild() {
        this.log('Testing build...');

        // Test Python server startup
        const pythonExe = path.join(this.pythonServerDir, 'dist', 'gt3-telemetry-server.exe');
        
        return new Promise((resolve, reject) => {
            const testProcess = spawn(pythonExe);
            let output = '';

            testProcess.stdout.on('data', (data) => {
                output += data.toString();
                if (output.includes('GT3 telemetry server running')) {
                    this.log('✅ Python server starts correctly');
                    testProcess.kill();
                    resolve();
                }
            });

            testProcess.stderr.on('data', (data) => {
                this.log(`Python server error: ${data}`);
            });

            setTimeout(() => {
                testProcess.kill();
                reject(new Error('Python server failed to start within 10 seconds'));
            }, 10000);
        });
    }

    async clean() {
        this.log('Cleaning build directories...');
        
        const dirsToClean = [
            path.join(this.pythonServerDir, 'build'),
            path.join(this.pythonServerDir, 'dist'),
            path.join(this.pythonServerDir, '__pycache__'),
            this.buildDir,
            this.distDir
        ];

        for (const dir of dirsToClean) {
            if (fs.existsSync(dir)) {
                fs.rmSync(dir, { recursive: true, force: true });
                this.log(`Cleaned ${dir}`);
            }
        }
    }

    async buildAll() {
        try {
            this.log('Starting GT3 AI Coaching build process...');
            
            await this.checkDependencies();
            await this.buildPythonServer();
            await this.buildElectronApp();
            await this.createInstaller();
            await this.testBuild();
            
            this.log('🎉 Build completed successfully!');
            this.log('');
            this.log('Output files:');
            this.log(`  Python server: ${path.join(this.pythonServerDir, 'dist', 'gt3-telemetry-server.exe')}`);
            this.log(`  Installer: ${path.join(this.distDir, 'GT3-AI-Coaching-Setup.exe')}`);
            this.log('');
            this.log('Ready for distribution! 🏎️');
            
        } catch (error) {
            this.log(`❌ Build failed: ${error.message}`);
            process.exit(1);
        }
    }
}

// CLI usage
if (require.main === module) {
    const builder = new GT3Builder();
    
    const command = process.argv[2];
    
    switch (command) {
        case 'clean':
            builder.clean();
            break;
        case 'python':
            builder.buildPythonServer();
            break;
        case 'electron':
            builder.buildElectronApp();
            break;
        case 'test':
            builder.testBuild();
            break;
        default:
            builder.buildAll();
    }
}

module.exports = GT3Builder;