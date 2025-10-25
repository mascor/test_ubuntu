```python
#!/usr/bin/env python3

import subprocess
import os
import sys
import time
import tempfile
import shutil
import re

def run_cmd(cmd, check=True):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip()

def check_dependencies():
    required_cmds = ['sysbench', 'lscpu', 'free', 'df', 'uname', 'lsb_release']
    missing = []
    for cmd in required_cmds:
        stdout, _ = run_cmd(f"which {cmd}", check=False)
        if not stdout:
            missing.append(cmd)
    
    if missing:
        print(f"Comandi mancanti: {', '.join(missing)}")
        print("Installa con: sudo apt install sysbench lsb-release")
        sys.exit(1)

def get_system_info():
    info = {}
    info['hostname'], _ = run_cmd("hostname")
    info['distro'], _ = run_cmd("lsb_release -ds")
    info['kernel'], _ = run_cmd("uname -r")
    
    lscpu_out, _ = run_cmd("lscpu")
    for line in lscpu_out.split('\n'):
        if 'Model name:' in line:
            info['cpu_model'] = line.split(':', 1)[1].strip()
            break
    
    info['cores'], _ = run_cmd("nproc")
    
    free_out, _ = run_cmd("free -h")
    for line in free_out.split('\n'):
        if line.startswith('Mem:'):
            parts = line.split()
            info['ram_total'] = parts[1]
            break
    
    df_out, _ = run_cmd("df -h /")
    for line in df_out.split('\n'):
        if line.startswith('/dev/'):
            parts = line.split()
            info['disk_total'] = parts[1]
            info['disk_free'] = parts[3]
            break
    
    return info

def parse_sysbench_cpu(output):
    total_time = None
    events_per_sec = None
    
    for line in output.split('\n'):
        if 'total time:' in line:
            match = re.search(r'total time:\s*([\d.]+)s', line)
            if match:
                total_time = match.group(1) + 's'
        elif 'events per second:' in line:
            match = re.search(r'events per second:\s*([\d.]+)', line)
            if match:
                events_per_sec = match.group(1)
    
    return total_time, events_per_sec

def bench_cpu():
    results = {}
    
    stdout, _ = run_cmd("sysbench cpu run")
    total_time, events_per_sec = parse_sysbench_cpu(stdout)
    results['single'] = {'total_time': total_time, 'events_per_sec': events_per_sec}
    
    nproc, _ = run_cmd("nproc")
    stdout, _ = run_cmd(f"sysbench cpu --threads={nproc} run")
    total_time, events_per_sec = parse_sysbench_cpu(stdout)
    results['multi'] = {'total_time': total_time, 'events_per_sec': events_per_sec}
    
    return results

def parse_sysbench_memory(output):
    transferred = None
    speed = None
    
    for line in output.split('\n'):
        if 'transferred (' in line:
            match = re.search(r'transferred \(([\d.]+\s*\w+)\)', line)
            if match:
                transferred = match.group(1)
        elif 'MiB/sec' in line and 'transferred' in line:
            match = re.search(r'([\d.]+)\s*MiB/sec', line)
            if match:
                speed = match.group(1) + ' MiB/sec'
    
    return transferred, speed

def bench_memory():
    results = {}
    
    stdout, _ = run_cmd("sysbench memory run")
    transferred, speed = parse_sysbench_memory(stdout)
    results['default'] = {'transferred': transferred, 'speed': speed}
    
    stdout, _ = run_cmd("sysbench memory --memory-block-size=1M --memory-total-size=5G run")
    transferred, speed = parse_sysbench_memory(stdout)
    results['large'] = {'transferred': transferred, 'speed': speed}
    
    return results

def parse_sysbench_fileio(output):
    read_mib = None
    write_mib = None
    avg_latency = None
    requests_per_sec = None
    
    for line in output.split('\n'):
        if 'read, MiB/s:' in line:
            match = re.search(r'read, MiB/s:\s*([\d.]+)', line)
            if match:
                read_mib = match.group(1) + ' MiB/s'
        elif 'written, MiB/s:' in line:
            match = re.search(r'written, MiB/s:\s*([\d.]+)', line)
            if match:
                write_mib = match.group(1) + ' MiB/s'
        elif 'avg:' in line and 'ms' in line:
            match = re.search(r'avg:\s*([\d.]+)', line)
            if match:
                avg_latency = match.group(1) + ' ms'
        elif 'reads/s:' in line or 'writes/s:' in line:
            match = re.search(r's:\s*([\d.]+)', line)
            if match:
                requests_per_sec = match.group(1)
    
    return read_mib, write_mib, avg_latency, requests_per_sec

def bench_io():
    tmpdir = tempfile.mkdtemp(prefix='sysbench_')
    old_cwd = os.getcwd()
    os.chdir(tmpdir)
    
    results = {}
    
    try:
        run_cmd("sysbench fileio --file-total-size=5G --file-num=5 prepare")
        
        tests = [
            ('seq_read', 'seqrd', '1M'),
            ('seq_write', 'seqwr', '1M'),
            ('rnd_read', 'rndrd', '4k'),
            ('rnd_write', 'rndwr', '4k')
        ]
        
        for test_name, test_mode, block_size in tests:
            cmd = f"sysbench fileio --file-total-size=5G --file-num=5 --file-test-mode={test_mode} --file-block-size={block_size} run"
            stdout, _ = run_cmd(cmd)
            read_mib, write_mib, avg_latency, requests_per_sec = parse_sysbench_fileio(stdout)
            
            results[test_name] = {
                'read': read_mib,
                'write': write_mib,
                'latency': avg_latency,
                'requests': requests_per_sec
            }
        
        run_cmd("sysbench fileio --file-total-size=5G --file-num=5 cleanup")
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    return results

def main():
    start_time = time.time()
    
    check_dependencies()
    
    sys_info = get_system_info()
    cpu_results = bench_cpu()
    mem_results = bench_memory()
    io_results = bench_io()
    
    duration = time.time() - start_time
    
    print("\n=== BENCHMARK HOST ===")
    print(f"Hostname: {sys_info['hostname']}")
    print(f"Distro: {sys_info['distro']}")
    print(f"Kernel: {sys_info['kernel']}")
    print(f"CPU model: {sys_info['cpu_model']}")
    print(f"CPU cores(logici): {sys_info['cores']}")
    print(f"RAM totale: {sys_info['ram_total']}")
    print(f"Disk root fs: {sys_info['disk_total']} (totale) / {sys_info['disk_free']} (libero)")
    
    print("\n=== CPU ===")
    print(f"[1 thread]   total time: {cpu_results['single']['total_time']}")
    print(f"             events/s : {cpu_results['single']['events_per_sec']}")
    print(f"[all cores]  total time: {cpu_results['multi']['total_time']}")
    print(f"             events/s : {cpu_results['multi']['events_per_sec']}")
    
    print("\n=== MEMORIA ===")
    print(f"default run:   trasferito={mem_results['default']['transferred']}, speed={mem_results['default']['speed']}")
    print(f"large 5G run:  trasferito={mem_results['large']['transferred']}, speed={mem_results['large']['speed']}")
    
    print("\n=== DISCO ===")
    print(f"seq read : {io_results['seq_read']['read']}")
    print(f"seq write: {io_results['seq_write']['write']}")
    print(f"rnd read : {io_results['rnd_read']['read']}")
    print(f"rnd write: {io_results['rnd_write']['write']}")
    
    print(f"\nDurata totale benchmark (s): {duration:.2f}")

if __name__ == "__main__":
    main()
```
