import subprocess
import os
import sys
import time
import tempfile
import shutil
import re
import json
from datetime import datetime

def run_cmd(cmd, check=True):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip()

def check_dependencies():
    print("🔍 Controllo dipendenze...")
    required_cmds = ['sysbench', 'lscpu', 'free', 'df', 'uname', 'lsb_release']
    missing = []
    for cmd in required_cmds:
        stdout, _ = run_cmd(f"which {cmd}", check=False)
        if not stdout:
            missing.append(cmd)
    
    if missing:
        print(f"❌ Comandi mancanti: {', '.join(missing)}")
        print("Installa con: sudo apt install sysbench lsb-release")
        sys.exit(1)
    print("✅ Tutte le dipendenze sono installate")

def get_system_info():
    print("📋 Raccolta informazioni di sistema...")
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
    
    print("✅ Informazioni di sistema raccolte")
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
    print("🚀 Inizio benchmark CPU...")
    results = {}
    
    print("   ⏱️ Esecuzione test CPU single-thread...")
    stdout, _ = run_cmd("sysbench cpu run")
    total_time, events_per_sec = parse_sysbench_cpu(stdout)
    results['single'] = {'total_time': total_time, 'events_per_sec': events_per_sec}
    
    nproc, _ = run_cmd("nproc")
    print(f"   ⏱️ Esecuzione test CPU multi-thread ({nproc} cores)...")
    stdout, _ = run_cmd(f"sysbench cpu --threads={nproc} run")
    total_time, events_per_sec = parse_sysbench_cpu(stdout)
    results['multi'] = {'total_time': total_time, 'events_per_sec': events_per_sec}
    
    print("✅ Benchmark CPU completato")
    return results

def parse_sysbench_memory(output):
    transferred = None
    speed = None
    
    for line in output.split('\n'):
        # Cerca la linea come "98550.87 MiB transferred (9854.32 MiB/sec)"
        if 'MiB transferred' in line and 'MiB/sec' in line:
            # Estrae i dati trasferiti
            match_transferred = re.search(r'([\d.]+)\s*MiB transferred', line)
            if match_transferred:
                transferred = match_transferred.group(1) + ' MiB'
            
            # Estrae la velocità
            match_speed = re.search(r'\(([\d.]+)\s*MiB/sec\)', line)
            if match_speed:
                speed = match_speed.group(1) + ' MiB/sec'
    
    return transferred, speed

def bench_memory():
    print("💾 Inizio benchmark Memoria...")
    results = {}
    
    print("   ⏱️ Esecuzione test memoria (default settings)...")
    stdout, stderr = run_cmd("sysbench memory run")
    transferred, speed = parse_sysbench_memory(stdout)
    if not transferred or not speed:
        print(f"   ⚠️  Debug - output catturato: {stdout[:200]}...")
    results['default'] = {'transferred': transferred, 'speed': speed}
    
    print("   ⏱️ Esecuzione test memoria (large 5GB blocks)...")
    stdout, stderr = run_cmd("sysbench memory --memory-block-size=1M --memory-total-size=5G run")
    transferred, speed = parse_sysbench_memory(stdout)
    if not transferred or not speed:
        print(f"   ⚠️  Debug - output catturato: {stdout[:200]}...")
    results['large'] = {'transferred': transferred, 'speed': speed}
    
    print("✅ Benchmark Memoria completato")
    return results

def parse_sysbench_fileio(output):
    read_mib = None
    write_mib = None
    avg_latency = None
    reads_per_sec = None
    writes_per_sec = None
    
    for line in output.split('\n'):
        line = line.strip()
        
        # Parsing throughput
        if 'read, MiB/s:' in line:
            match = re.search(r'read, MiB/s:\s*([\d.]+)', line)
            if match:
                read_mib = match.group(1) + ' MiB/s'
        elif 'written, MiB/s:' in line:
            match = re.search(r'written, MiB/s:\s*([\d.]+)', line)
            if match:
                write_mib = match.group(1) + ' MiB/s'
        
        # Parsing operations per second
        elif 'reads/s:' in line:
            match = re.search(r'reads/s:\s*([\d.]+)', line)
            if match:
                reads_per_sec = match.group(1)
        elif 'writes/s:' in line:
            match = re.search(r'writes/s:\s*([\d.]+)', line)
            if match:
                writes_per_sec = match.group(1)
        
        # Parsing latency
        elif 'avg:' in line and any(word in line for word in ['ms', 'latency']):
            match = re.search(r'avg:\s*([\d.]+)', line)
            if match:
                avg_latency = match.group(1) + ' ms'
    
    # Determina quale valore IOPS usare basandosi sul tipo di test
    requests_per_sec = reads_per_sec if reads_per_sec and float(reads_per_sec) > 0 else writes_per_sec
    
    return read_mib, write_mib, avg_latency, requests_per_sec

def bench_io():
    print("💽 Inizio benchmark Disco I/O...")
    tmpdir = tempfile.mkdtemp(prefix='sysbench_')
    old_cwd = os.getcwd()
    os.chdir(tmpdir)
    
    results = {}
    
    try:
        print("   📂 Preparazione file di test (5GB)...")
        run_cmd("sysbench fileio --file-total-size=5G --file-num=5 prepare")
        
        tests = [
            ('seq_read', 'seqrd', '1M', 'lettura sequenziale'),
            ('seq_write', 'seqwr', '1M', 'scrittura sequenziale'),
            ('rnd_read', 'rndrd', '4k', 'lettura randomica'),
            ('rnd_write', 'rndwr', '4k', 'scrittura randomica')
        ]
        
        for test_name, test_mode, block_size, description in tests:
            print(f"   ⏱️ Esecuzione test {description} (block size {block_size})...")
            cmd = f"sysbench fileio --file-total-size=5G --file-num=5 --file-test-mode={test_mode} --file-block-size={block_size} run"
            stdout, _ = run_cmd(cmd)
            read_mib, write_mib, avg_latency, requests_per_sec = parse_sysbench_fileio(stdout)
            
            results[test_name] = {
                'read': read_mib,
                'write': write_mib,
                'latency': avg_latency,
                'requests': requests_per_sec
            }
        
        print("   🧹 Pulizia file di test...")
        run_cmd("sysbench fileio --file-total-size=5G --file-num=5 cleanup")
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    print("✅ Benchmark Disco I/O completato")
    return results

def save_json_report(sys_info, cpu_results, mem_results, io_results, duration):
    """Salva i risultati del benchmark in formato JSON per analisi LLM"""
    
    # Struttura dati completa per il JSON
    benchmark_data = {
        "benchmark_info": {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "tool_version": "sysbench_analyzer_v1.0",
            "test_date": datetime.now().strftime("%Y-%m-%d"),
            "test_time": datetime.now().strftime("%H:%M:%S")
        },
        "system_info": {
            "hostname": sys_info.get('hostname', 'unknown'),
            "os_distribution": sys_info.get('distro', 'unknown'),
            "kernel_version": sys_info.get('kernel', 'unknown'),
            "cpu_model": sys_info.get('cpu_model', 'unknown'),
            "cpu_cores": int(sys_info.get('cores', 0)) if sys_info.get('cores', '0').isdigit() else 0,
            "ram_total": sys_info.get('ram_total', 'unknown'),
            "disk_total": sys_info.get('disk_total', 'unknown'),
            "disk_free": sys_info.get('disk_free', 'unknown')
        },
        "cpu_benchmark": {
            "single_thread": {
                "total_time_seconds": float(cpu_results['single']['total_time'].replace('s', '')) if cpu_results['single']['total_time'] else 0,
                "events_per_second": float(cpu_results['single']['events_per_sec']) if cpu_results['single']['events_per_sec'] else 0,
                "raw_total_time": cpu_results['single']['total_time'],
                "raw_events_per_sec": cpu_results['single']['events_per_sec']
            },
            "multi_thread": {
                "total_time_seconds": float(cpu_results['multi']['total_time'].replace('s', '')) if cpu_results['multi']['total_time'] else 0,
                "events_per_second": float(cpu_results['multi']['events_per_sec']) if cpu_results['multi']['events_per_sec'] else 0,
                "raw_total_time": cpu_results['multi']['total_time'],
                "raw_events_per_sec": cpu_results['multi']['events_per_sec'],
                "threads_used": int(sys_info.get('cores', 0)) if sys_info.get('cores', '0').isdigit() else 0
            }
        },
        "memory_benchmark": {
            "default_test": {
                "transferred": mem_results['default']['transferred'],
                "speed_mib_per_sec": float(mem_results['default']['speed'].replace(' MiB/sec', '')) if mem_results['default']['speed'] and 'MiB/sec' in str(mem_results['default']['speed']) else 0,
                "raw_speed": mem_results['default']['speed']
            },
            "large_test_5gb": {
                "transferred": mem_results['large']['transferred'],
                "speed_mib_per_sec": float(mem_results['large']['speed'].replace(' MiB/sec', '')) if mem_results['large']['speed'] and 'MiB/sec' in str(mem_results['large']['speed']) else 0,
                "raw_speed": mem_results['large']['speed']
            }
        },
        "io_benchmark": {
            "sequential_read": {
                "speed_mib_per_sec": float(io_results['seq_read']['read'].replace(' MiB/s', '')) if io_results['seq_read']['read'] and 'MiB/s' in io_results['seq_read']['read'] else 0,
                "raw_speed": io_results['seq_read']['read'],
                "latency_ms": float(io_results['seq_read']['latency'].replace(' ms', '')) if io_results['seq_read']['latency'] and 'ms' in io_results['seq_read']['latency'] else 0,
                "requests_per_sec": float(io_results['seq_read']['requests']) if io_results['seq_read']['requests'] else 0,
                "block_size": "1M"
            },
            "sequential_write": {
                "speed_mib_per_sec": float(io_results['seq_write']['write'].replace(' MiB/s', '')) if io_results['seq_write']['write'] and 'MiB/s' in io_results['seq_write']['write'] else 0,
                "raw_speed": io_results['seq_write']['write'],
                "latency_ms": float(io_results['seq_write']['latency'].replace(' ms', '')) if io_results['seq_write']['latency'] and 'ms' in io_results['seq_write']['latency'] else 0,
                "requests_per_sec": float(io_results['seq_write']['requests']) if io_results['seq_write']['requests'] else 0,
                "block_size": "1M"
            },
            "random_read": {
                "speed_mib_per_sec": float(io_results['rnd_read']['read'].replace(' MiB/s', '')) if io_results['rnd_read']['read'] and 'MiB/s' in io_results['rnd_read']['read'] else 0,
                "raw_speed": io_results['rnd_read']['read'],
                "latency_ms": float(io_results['rnd_read']['latency'].replace(' ms', '')) if io_results['rnd_read']['latency'] and 'ms' in io_results['rnd_read']['latency'] else 0,
                "requests_per_sec": float(io_results['rnd_read']['requests']) if io_results['rnd_read']['requests'] else 0,
                "block_size": "4k"
            },
            "random_write": {
                "speed_mib_per_sec": float(io_results['rnd_write']['write'].replace(' MiB/s', '')) if io_results['rnd_write']['write'] and 'MiB/s' in io_results['rnd_write']['write'] else 0,
                "raw_speed": io_results['rnd_write']['write'],
                "latency_ms": float(io_results['rnd_write']['latency'].replace(' ms', '')) if io_results['rnd_write']['latency'] and 'ms' in io_results['rnd_write']['latency'] else 0,
                "requests_per_sec": float(io_results['rnd_write']['requests']) if io_results['rnd_write']['requests'] else 0,
                "block_size": "4k"
            }
        },
        "performance_summary": {
            "cpu_single_thread_score": float(cpu_results['single']['events_per_sec']) if cpu_results['single']['events_per_sec'] else 0,
            "cpu_multi_thread_score": float(cpu_results['multi']['events_per_sec']) if cpu_results['multi']['events_per_sec'] else 0,
            "memory_bandwidth_mib_sec": float(mem_results['large']['speed'].replace(' MiB/sec', '')) if mem_results['large']['speed'] and 'MiB/sec' in mem_results['large']['speed'] else 0,
            "io_seq_read_mib_sec": float(io_results['seq_read']['read'].replace(' MiB/s', '')) if io_results['seq_read']['read'] and 'MiB/s' in io_results['seq_read']['read'] else 0,
            "io_seq_write_mib_sec": float(io_results['seq_write']['write'].replace(' MiB/s', '')) if io_results['seq_write']['write'] and 'MiB/s' in io_results['seq_write']['write'] else 0,
            "io_random_read_iops": float(io_results['rnd_read']['requests']) if io_results['rnd_read']['requests'] else 0,
            "io_random_write_iops": float(io_results['rnd_write']['requests']) if io_results['rnd_write']['requests'] else 0
        }
    }
    
    # Nome file con timestamp
    hostname = sys_info.get('hostname', 'unknown')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"benchmark_{hostname}_{timestamp}.json"
    
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(benchmark_data, f, indent=2, ensure_ascii=False)
        print(f"📄 Report JSON salvato: {json_filename}")
        return json_filename
    except Exception as e:
        print(f"❌ Errore nel salvare il file JSON: {e}")
        return None

def main():
    print("🏁 Avvio benchmark completo del sistema...")
    start_time = time.time()
    
    check_dependencies()
    
    sys_info = get_system_info()
    cpu_results = bench_cpu()
    mem_results = bench_memory()
    io_results = bench_io()
    
    duration = time.time() - start_time
    print("📊 Generazione report finale...")
    
    # Salva il report JSON per analisi LLM
    json_filename = save_json_report(sys_info, cpu_results, mem_results, io_results, duration)
    
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
    
    print(f"\n⏰ Durata totale benchmark: {duration:.2f} secondi")
    print("🎉 Benchmark completato con successo!")
    
    if json_filename:
        print(f"\n📋 Per confronti LLM usa il file: {json_filename}")

if __name__ == "__main__":
    main()