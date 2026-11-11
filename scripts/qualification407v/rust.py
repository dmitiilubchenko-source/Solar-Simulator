from pathlib import Path
import subprocess,os,shutil
S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v');W=Path('C:/Users/Admin/Documents/Codex/Solar407V-20261111');cargo=Path.home()/'.cargo/bin/cargo.exe';rustc=cargo.with_name('rustc.exe')
sysroot=Path(subprocess.check_output([str(rustc),'--print','sysroot'],text=True).strip())
os.environ['PATH']=str(cargo.parent)+os.pathsep+str(sysroot/'lib/rustlib/x86_64-pc-windows-gnu/bin/self-contained')+os.pathsep+'C:/Users/Admin/Desktop/Solar-simulator/.tools/msys2/mingw64/bin'+os.pathsep+os.environ['PATH']
for n in ('solar_core','solar_native'):subprocess.run([str(cargo),'fmt','--manifest-path',str(S/f'rust/{n}/Cargo.toml'),'--check'],check=True)
for action in ('test','build'):
    subprocess.run([str(cargo),action,'--release','--locked','--offline','--manifest-path',str(S/'rust/solar_core/Cargo.toml'),'--target-dir',str(W/'target-native')],check=True)
p=S/'rust/solar_core/target/release';p.mkdir(parents=True,exist_ok=True);shutil.copyfile(W/'target-native/release/solar_core.exe',p/'solar_core.exe')
