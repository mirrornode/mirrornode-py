#!/usr/bin/env python3
"""
THOTH :: DESKTOP COMMANDER PRE-FLIGHT VERIFICATION
MIRRORNODE v0.2.0 Hermes - System Readiness Assessment

Execution: python3 thoth_preflight.py
Output: Full deployment readiness report with PASS/FAIL per section
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

class ThothPreflight:
    def __init__(self, base_path: str = None):
        """Initialize THOTH pre-flight checker with optional base path override."""
        if base_path:
            self.base_path = Path(base_path).expanduser()
        else:
            # Try primary path first
            primary = Path("~/dev/mirrornode-py/").expanduser()
            fallback = Path("~/Desktop/MIRRORNODE/").expanduser()
            
            if primary.exists():
                self.base_path = primary
            elif fallback.exists():
                self.base_path = fallback
            else:
                self.base_path = primary  # Default even if doesn't exist yet
        
        self.results = {
            "sections": {},
            "timestamp": datetime.now().isoformat(),
            "base_path": str(self.base_path),
            "overall_status": None
        }
        self.check_count = 0
        self.pass_count = 0
        self.fail_count = 0
        self.halt_on_fail = False
    
    def log_header(self, text: str):
        """Log section header."""
        print(f"\n{BLUE}{BOLD}{'='*80}{RESET}")
        print(f"{BLUE}{BOLD}{text}{RESET}")
        print(f"{BLUE}{BOLD}{'='*80}{RESET}\n")
    
    def log_check(self, check_id: str, status: str, message: str, details: str = None):
        """Log individual check result."""
        self.check_count += 1
        if status == "PASS":
            self.pass_count += 1
            symbol = f"{GREEN}✓{RESET}"
        elif status == "FAIL":
            self.fail_count += 1
            symbol = f"{RED}✗{RESET}"
        else:  # WARN
            symbol = f"{YELLOW}⚠{RESET}"
        
        print(f"{symbol} {BOLD}{check_id}{RESET}: {message}")
        if details:
            print(f"  {details}")
        
        return status
    
    def run_command(self, cmd: str, shell: bool = True) -> Tuple[str, str, int]:
        """Execute shell command and return stdout, stderr, returncode."""
        try:
            result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=5)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", 1
        except Exception as e:
            return "", str(e), 1
    
    def section_1_filesystem(self):
        """SECTION 1: FILESYSTEM & REPOSITORY STATE"""
        self.log_header("SECTION 1: FILESYSTEM & REPOSITORY STATE")
        section_results = {}
        
        # Check 1.1 - Hermes v0.2.0 Seed Tree
        expected_dirs = [
            "core/events", "core/adapters", "core/bridge", "core/engines",
            "hud/websocket", "tests", "scripts"
        ]
        found_dirs = []
        for dir_name in expected_dirs:
            dir_path = self.base_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                found_dirs.append(dir_name)
        
        status = "PASS" if len(found_dirs) == len(expected_dirs) else "WARN"
        section_results["1.1"] = self.log_check(
            "1.1 - Hermes v0.2.0 Seed Tree",
            status,
            f"Found {len(found_dirs)}/{len(expected_dirs)} expected subdirectories",
            f"Location: {self.base_path}\nFound: {', '.join(found_dirs) if found_dirs else 'NONE'}"
        )
        
        # Check 1.2 - Canonical Files
        expected_files = ["pyproject.toml", "README.md", ".gitignore", "Makefile"]
        found_files = []
        for file_name in expected_files:
            file_path = self.base_path / file_name
            if file_path.exists() and file_path.is_file():
                found_files.append(file_name)
        
        status = "PASS" if len(found_files) >= 3 else "WARN"
        section_results["1.2"] = self.log_check(
            "1.2 - Canonical Files Present",
            status,
            f"Found {len(found_files)}/{len(expected_files)} canonical files",
            f"Found: {', '.join(found_files) if found_files else 'NONE'}"
        )
        
        # Check 1.3 - Git Initialization
        git_status_output, _, git_rc = self.run_command(f"cd {self.base_path} && git status")
        if git_rc == 0:
            status = "PASS"
            message = "Git repository already initialized"
        else:
            status = "WARN"
            message = "Git repository not yet initialized (OK to init)"
        section_results["1.3"] = self.log_check("1.3 - Git Initialization", status, message)
        
        # Check 1.4 - Hermes Archive
        archive_paths = [
            Path("~/Desktop/hermes-v0.2.0.tar.gz").expanduser(),
            Path("~/.mirrornode/hermes/hermes-v0.2.0.tar.gz").expanduser()
        ]
        archive_found = any(p.exists() for p in archive_paths)
        status = "PASS" if archive_found else "WARN"
        section_results["1.4"] = self.log_check(
            "1.4 - Hermes v0.2.0 Archive",
            status,
            "Archive not yet downloaded (OK, can proceed)" if not archive_found else "Archive found"
        )
        
        self.results["sections"]["1_filesystem"] = section_results
        return all(v == "PASS" for v in section_results.values())
    
    def section_2_toolchain(self):
        """SECTION 2: DEVELOPMENT ENVIRONMENT & TOOLCHAIN"""
        self.log_header("SECTION 2: DEVELOPMENT ENVIRONMENT & TOOLCHAIN")
        section_results = {}
        
        # Check 2.1 - Python 3.12+
        python_version, _, rc = self.run_command("python3 --version")
        if rc == 0 and ("3.12" in python_version or "3.13" in python_version):
            status = "PASS"
        else:
            status = "FAIL"
        section_results["2.1"] = self.log_check(
            "2.1 - Python 3.12+ Installed",
            status,
            python_version if python_version else "Python not found"
        )
        
        # Check 2.2 - Poetry
        poetry_version, _, rc = self.run_command("poetry --version")
        status = "PASS" if rc == 0 else "FAIL"
        section_results["2.2"] = self.log_check(
            "2.2 - Poetry Package Manager",
            status,
            poetry_version if poetry_version else "Poetry not found"
        )
        
        # Check 2.3 - Docker
        docker_version, _, rc = self.run_command("docker --version")
        docker_ps, _, ps_rc = self.run_command("docker ps")
        status = "PASS" if rc == 0 and ps_rc == 0 else "WARN"
        section_results["2.3"] = self.log_check(
            "2.3 - Docker Installed and Running",
            status,
            docker_version if docker_version else "Docker not found or daemon not running"
        )
        
        # Check 2.4 - Git
        git_version, _, rc = self.run_command("git --version")
        status = "PASS" if rc == 0 else "FAIL"
        section_results["2.4"] = self.log_check(
            "2.4 - Git Installed",
            status,
            git_version if git_version else "Git not found"
        )
        
        # Check 2.5 - Essential CLI Tools
        tools = ["curl", "jq", "base64", "openssl"]
        found_tools = []
        for tool in tools:
            _, _, rc = self.run_command(f"which {tool}")
            if rc == 0:
                found_tools.append(tool)
        
        status = "PASS" if len(found_tools) >= 3 else "WARN"
        section_results["2.5"] = self.log_check(
            "2.5 - Essential CLI Tools",
            status,
            f"Found {len(found_tools)}/{len(tools)} tools",
            f"Found: {', '.join(found_tools) if found_tools else 'NONE'}"
        )
        
        # Check 2.6 - Flyctl (optional)
        flyctl_version, _, rc = self.run_command("flyctl version")
        status = "WARN"  # Always soft
        section_results["2.6"] = self.log_check(
            "2.6 - Flyctl (Fly.io CLI)",
            status,
            "Flyctl not required for local testing" if rc != 0 else f"Found: {flyctl_version}"
        )
        
        self.results["sections"]["2_toolchain"] = section_results
        # Hard requirements: 2.1, 2.2, 2.4
        hard_reqs = section_results.get("2.1") == "PASS" and section_results.get("2.2") == "PASS" and section_results.get("2.4") == "PASS"
        return hard_reqs
    
    def section_3_crypto(self):
        """SECTION 3: CRYPTOGRAPHIC SPINE VALIDATION"""
        self.log_header("SECTION 3: CRYPTOGRAPHIC SPINE VALIDATION")
        section_results = {}
        
        # Check 3.1 - Oracle Vault Directory
        vault_path = Path("~/.mirrornode/oracle/").expanduser()
        vault_subdirs = ["keys", "logs", "tmp"]
        found_subdirs = []
        
        # Create vault if it doesn't exist
        for subdir in vault_subdirs:
            subdir_path = vault_path / subdir
            if not subdir_path.exists():
                try:
                    subdir_path.mkdir(parents=True, exist_ok=True)
                    found_subdirs.append(subdir)
                except Exception as e:
                    pass
            else:
                found_subdirs.append(subdir)
        
        status = "PASS" if len(found_subdirs) == len(vault_subdirs) else "WARN"
        section_results["3.1"] = self.log_check(
            "3.1 - Oracle Vault Directory Ready",
            status,
            f"Vault at {vault_path}: {len(found_subdirs)}/{len(vault_subdirs)} subdirs",
            f"Subdirs: {', '.join(found_subdirs)}"
        )
        
        # Check 3.2 - Ed25519 Key Generation Utility
        keygen_path = self.base_path / "scripts" / "generate_keys.py"
        if keygen_path.exists():
            status = "PASS"
            message = "Key generation utility found"
        else:
            status = "WARN"
            message = "Key generation utility not yet present (will be added)"
        section_results["3.2"] = self.log_check("3.2 - Ed25519 Key Generation Utility", status, message)
        
        # Check 3.3 - Cryptographic Libraries
        try:
            import cryptography
            import pydantic
            from cryptography.hazmat.primitives.asymmetric import ed25519
            status = "PASS"
            message = "Required crypto libraries available"
        except ImportError:
            status = "WARN"
            message = "Crypto libraries not yet installed (will install via poetry)"
        section_results["3.3"] = self.log_check("3.3 - Cryptographic Libraries", status, message)
        
        # Check 3.4 - .gitignore Protection
        gitignore_path = self.base_path / ".gitignore"
        patterns_to_check = ["mirrornode", ".env", "key", "pem"]
        found_patterns = []
        
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r') as f:
                    gitignore_content = f.read()
                    for pattern in patterns_to_check:
                        if pattern in gitignore_content:
                            found_patterns.append(pattern)
            except Exception as e:
                pass
        
        status = "PASS" if len(found_patterns) >= 2 else "WARN"
        section_results["3.4"] = self.log_check(
            "3.4 - .gitignore Secret Protection",
            status,
            f"Found {len(found_patterns)}/{len(patterns_to_check)} protection patterns",
            f"Patterns: {', '.join(found_patterns) if found_patterns else 'NONE'}"
        )
        
        self.results["sections"]["3_crypto"] = section_results
        return True  # All soft requirements
    
    def section_4_dependencies(self):
        """SECTION 4: DEPENDENCY & CODE STRUCTURE VALIDATION"""
        self.log_header("SECTION 4: DEPENDENCY & CODE STRUCTURE VALIDATION")
        section_results = {}
        
        # Check 4.1 - pyproject.toml Valid
        pyproject_path = self.base_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomli
                with open(pyproject_path, 'rb') as f:
                    tomli.load(f)
                status = "PASS"
                message = "pyproject.toml is valid TOML"
            except Exception as e:
                status = "WARN"
                message = f"pyproject.toml exists but may have syntax issues: {str(e)[:50]}"
        else:
            status = "WARN"
            message = "pyproject.toml not yet created"
        section_results["4.1"] = self.log_check("4.1 - pyproject.toml Valid", status, message)
        
        # Check 4.2 - Core Module Structure
        core_path = self.base_path / "core"
        py_files = []
        if core_path.exists():
            try:
                py_files = [f for f in core_path.rglob("*.py") if f.is_file()]
            except Exception as e:
                pass
        
        status = "PASS" if len(py_files) >= 4 else "WARN"
        section_results["4.2"] = self.log_check(
            "4.2 - Core Module Structure",
            status,
            f"Found {len(py_files)}/4+ expected .py files",
            f"Files: {', '.join(f.name for f in py_files[:5])}" if py_files else "NONE"
        )
        
        # Check 4.3 - Test Suite
        tests_path = self.base_path / "tests"
        test_files = []
        if tests_path.exists():
            try:
                test_files = [f for f in tests_path.glob("test_*.py") or tests_path.glob("*_test.py")]
            except Exception as e:
                pass
        
        status = "PASS" if len(test_files) >= 1 else "WARN"
        section_results["4.3"] = self.log_check(
            "4.3 - Test Suite Skeleton",
            status,
            f"Found {len(test_files)} test files (OK if 0, will populate)",
            f"Files: {', '.join(f.name for f in test_files)}" if test_files else "Tests directory ready for seeding"
        )
        
        # Check 4.4 - Scripts Directory
        scripts_path = self.base_path / "scripts"
        script_files = []
        if scripts_path.exists():
            try:
                script_files = [f for f in scripts_path.glob("*") if f.suffix in [".sh", ".py"]]
            except Exception as e:
                pass
        
        status = "PASS" if len(script_files) >= 2 else "WARN"
        section_results["4.4"] = self.log_check(
            "4.4 - Scripts Directory Populated",
            status,
            f"Found {len(script_files)} scripts",
            f"Scripts: {', '.join(f.name for f in script_files[:5])}" if script_files else "NONE"
        )
        
        self.results["sections"]["4_dependencies"] = section_results
        return True  # All soft
    
    def section_5_lattice(self):
        """SECTION 5: MULTI-NODE LATTICE READINESS"""
        self.log_header("SECTION 5: MULTI-NODE LATTICE READINESS")
        section_results = {}
        
        # Check 5.1 - Bridge Config Template
        env_paths = [
            self.base_path / "oracle.env",
            self.base_path / ".env.example",
            Path("~/.mirrornode/oracle.env").expanduser()
        ]
        env_found = any(p.exists() for p in env_paths)
        status = "PASS" if env_found else "WARN"
        section_results["5.1"] = self.log_check(
            "5.1 - Bridge Configuration Template",
            status,
            "Config template found" if env_found else "Config template not yet created"
        )
        
        # Check 5.2 - Adapter/Engine Names
        adapter_names = ["claude", "grok", "theia", "merlin", "perplexity"]
        engine_names = ["rotan", "trism", "inoesso", "numeraethe", "praesoetic"]
        
        found_names = []
        for py_file in self.base_path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    for name in adapter_names + engine_names:
                        if name in content.lower():
                            found_names.append(name)
            except:
                pass
        
        found_names = list(set(found_names))
        status = "PASS" if len(found_names) >= 3 else "WARN"
        section_results["5.2"] = self.log_check(
            "5.2 - Adapter/Engine Names Match Lattice",
            status,
            f"Found {len(found_names)} lattice node references",
            f"Nodes: {', '.join(found_names[:5])}" if found_names else "NONE"
        )
        
        # Check 5.3 - Event Contract Alignment
        event_contract_found = False
        for py_file in self.base_path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    if "MirrorNodeEvent" in content or ("node" in content and "timestamp" in content and "signature" in content):
                        event_contract_found = True
                        break
            except:
                pass
        
        status = "PASS" if event_contract_found else "WARN"
        section_results["5.3"] = self.log_check(
            "5.3 - Event Contract Alignment",
            status,
            "Event model with required fields found" if event_contract_found else "Event model not yet defined"
        )
        
        self.results["sections"]["5_lattice"] = section_results
        return True  # All soft
    
    def section_6_deployment(self):
        """SECTION 6: DEPLOYMENT READINESS"""
        self.log_header("SECTION 6: DEPLOYMENT READINESS")
        section_results = {}
        
        # Check 6.1 - Makefile
        makefile_path = self.base_path / "Makefile"
        makefile_targets = []
        if makefile_path.exists():
            try:
                with open(makefile_path, 'r') as f:
                    content = f.read()
                    for line in content.split('\n'):
                        if ':' in line and not line.startswith('\t'):
                            target = line.split(':')[0].strip()
                            if target:
                                makefile_targets.append(target)
            except:
                pass
        
        expected_targets = ["preflight", "keys", "env", "first-boot", "docker-build", "fly-deploy"]
        found_targets = [t for t in expected_targets if t in makefile_targets]
        status = "PASS" if len(found_targets) >= 4 else "WARN"
        section_results["6.1"] = self.log_check(
            "6.1 - Makefile Present and Sequenced",
            status,
            f"Found {len(found_targets)}/{len(expected_targets)} deployment targets",
            f"Targets: {', '.join(found_targets)}" if found_targets else "NONE"
        )
        
        # Check 6.2 - Dockerfile
        dockerfile_path = self.base_path / "Dockerfile"
        if dockerfile_path.exists():
            status = "PASS"
            message = "Dockerfile found"
        else:
            status = "WARN"
            message = "Dockerfile not required for local testing"
        section_results["6.2"] = self.log_check("6.2 - Docker Support", status, message)
        
        # Check 6.3 - fly.toml
        fly_path = self.base_path / "fly.toml"
        if fly_path.exists():
            status = "PASS"
            message = "fly.toml found"
        else:
            status = "WARN"
            message = "fly.toml optional for local testing"
        section_results["6.3"] = self.log_check("6.3 - Fly.io Configuration", status, message)
        
        # Check 6.4 - Poetry Deps
        pyproject_path = self.base_path / "pyproject.toml"
        poetry_lock_path = self.base_path / "poetry.lock"
        has_deps = pyproject_path.exists() or poetry_lock_path.exists()
        status = "PASS" if has_deps else "WARN"
        section_results["6.4"] = self.log_check(
            "6.4 - Poetry Dependencies Declared",
            status,
            "Dependency spec found" if has_deps else "Dependencies not yet declared"
        )
        
        self.results["sections"]["6_deployment"] = section_results
        return True  # All soft
    
    def section_7_health(self):
        """SECTION 7: SYSTEM HEALTH & COHERENCE"""
        self.log_header("SECTION 7: SYSTEM HEALTH & COHERENCE")
        section_results = {}
        
        # Check 7.1 - No Stale Bytecode
        pyc_files = list(self.base_path.rglob("*.pyc"))
        pycache_dirs = list(self.base_path.rglob("__pycache__"))
        status = "PASS" if len(pyc_files) == 0 and len(pycache_dirs) == 0 else "WARN"
        section_results["7.1"] = self.log_check(
            "7.1 - No Critical Bytecode Conflicts",
            status,
            "Clean state (no .pyc or __pycache__)" if status == "PASS" else f"Found {len(pyc_files)} .pyc files and {len(pycache_dirs)} cache dirs (OK, will clean)"
        )
        
        # Check 7.2 - README Clarity
        readme_path = self.base_path / "README.md"
        if readme_path.exists():
            try:
                with open(readme_path, 'r') as f:
                    content = f.read()
                    status = "PASS" if len(content) > 50 else "WARN"
                    message = "README.md found with content"
            except:
                status = "WARN"
                message = "README.md exists but may be empty"
        else:
            status = "WARN"
            message = "README.md not yet created"
        section_results["7.2"] = self.log_check("7.2 - README Clarity", status, message)
        
        # Check 7.3 - Network Readiness (optional)
        _, _, ping_rc = self.run_command("ping -c 1 8.8.8.8", shell=True)
        status = "WARN"  # Always soft
        message = "Internet available" if ping_rc == 0 else "No internet (local testing only is OK)"
        section_results["7.3"] = self.log_check("7.3 - Network Readiness", status, message)
        
        self.results["sections"]["7_health"] = section_results
        return True  # All soft
    
    def generate_certificate(self):
        """Generate final deployment-ready certificate."""
        print(f"\n{BLUE}{BOLD}{'='*80}{RESET}")
        print(f"{BLUE}{BOLD}THOTH PRE-FLIGHT ASSESSMENT COMPLETE{RESET}")
        print(f"{BLUE}{BOLD}{'='*80}{RESET}\n")
        
        print(f"Base Path: {self.results['base_path']}")
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Total Checks: {self.check_count}")
        print(f"Passed: {GREEN}{self.pass_count}{RESET}")
        print(f"Failed: {RED}{self.fail_count}{RESET}\n")
        
        if self.fail_count == 0:
            print(f"{GREEN}{BOLD}✓ PRE-FLIGHT COMPLETE - SYSTEM READY FOR DEPLOYMENT{RESET}\n")
            print(f"{GREEN}=== DEPLOYMENT-READY CERTIFICATE ==={RESET}")
            print(f"{GREEN}System: MIRRORNODE v0.2.0 Hermes{RESET}")
            print(f"{GREEN}Status: PRE-FLIGHT COMPLETE{RESET}")
            print(f"{GREEN}All hard requirements satisfied.{RESET}\n")
            print(f"Next Actions:")
            print(f"  1. cd {self.base_path}")
            print(f"  2. poetry install")
            print(f"  3. poetry run pytest")
            print(f"  4. poetry run python3 scripts/generate_keys.py")
            print(f"  5. poetry run python3 scripts/run_bridge.sh\n")
            print(f"{GREEN}All systems go. Ready for Track Alpha deployment.{RESET}\n")
            self.results["overall_status"] = "PRE-FLIGHT COMPLETE"
        else:
            print(f"{RED}{BOLD}⚠ PRE-FLIGHT INCOMPLETE - REMEDIATION REQUIRED{RESET}\n")
            print(f"{RED}Failed checks:{RESET}")
            for section_name, checks in self.results["sections"].items():
                for check_id, status in checks.items():
                    if status == "FAIL":
                        print(f"  - {section_name}.{check_id}")
            print(f"\n{YELLOW}Review output above for remediation guidance.{RESET}\n")
            self.results["overall_status"] = "REMEDIATION REQUIRED"
        
        print(f"{BLUE}{BOLD}{'='*80}{RESET}\n")
    
    def run_all_checks(self):
        """Execute all pre-flight sections."""
        print(f"{BOLD}THOTH :: DESKTOP COMMANDER PRE-FLIGHT SEQUENCE{RESET}")
        print(f"Base Path: {self.base_path}")
        print(f"Initiating comprehensive system verification...\n")
        
        self.section_1_filesystem()
        self.section_2_toolchain()
        self.section_3_crypto()
        self.section_4_dependencies()
        self.section_5_lattice()
        self.section_6_deployment()
        self.section_7_health()
        
        self.generate_certificate()
        
        return self.results


def main():
    """Main execution."""
    import sys
    
    base_path = None
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    
    thoth = ThothPreflight(base_path=base_path)
    results = thoth.run_all_checks()
    
    # Exit with appropriate code
    sys.exit(0 if thoth.fail_count == 0 else 1)


if __name__ == "__main__":
    main()

# ---- OSIRIS EXPORT (forced, v1) ----
from pathlib import Path

def run_preflight(target: Path) -> dict:
    checks = []

    checks.append({
        "name": "Target exists",
        "pass": target.exists(),
        "category": "preflight",
    })

    checks.append({
        "name": "Target is directory",
        "pass": target.is_dir(),
        "category": "preflight",
    })

    passed = all(c["pass"] for c in checks)

    return {
        "pass": passed,
        "checks": checks,
    }
