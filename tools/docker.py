from pathlib import Path
import subprocess

def ensure_docker():
    try:
        # Check if Docker is installed and running
        subprocess.run(["docker", "info"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        raise Exception("Docker is not installed or not in PATH.")
    except subprocess.CalledProcessError:
        raise Exception("Docker is installed but not running or not accessible.")

def image_exists(image_name):
    try:
        # Check if image exists locally
        result = subprocess.run(
            ["docker", "images", "-q", image_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.stdout.strip():
            return True
        return False
    except subprocess.CalledProcessError:
        raise Exception("Failed to check images.")

def pull_image(image_name):
    subprocess.run(
        ["docker", "pull", image_name],
        check=True
    )

def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    result.stdout = (result.stdout or b"").decode("utf-8", errors="replace")
    result.stderr = (result.stderr or b"").decode("utf-8", errors="replace")
    return result

def run(image: str, host_src_dir: str, shell_cmd: str, timeout=None):
    host_src_dir = Path(host_src_dir)    
    return _run([
        "docker", "run", "--rm",
        "-v", f"{str(host_src_dir.resolve())}:/work",
        "-w", "/work",
        image, "bash", "-lc", shell_cmd
    ], timeout=timeout)