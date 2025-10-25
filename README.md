# 🚀 Sysbench System Analyzer

Un tool completo per il benchmarking delle prestazioni del sistema che utilizza sysbench per testare CPU, memoria e I/O disco, generando report dettagliati sia in formato human-readable che JSON per analisi automatizzate.

## 📋 Caratteristiche

- **Benchmark CPU**: Test single-thread e multi-thread
- **Benchmark Memoria**: Test con configurazioni default e large (5GB)
- **Benchmark I/O Disco**: Test sequenziali e randomici (lettura/scrittura)
- **Output informativo**: Messaggi con emoji per seguire il progresso
- **Export JSON**: File strutturato per confronti automatizzati e analisi LLM
- **Informazioni sistema**: Raccolta automatica delle specifiche hardware

## 🛠️ Requisiti

### Dipendenze Sistema
```bash
sudo apt update
sudo apt install sysbench lsb-release
```

### Dipendenze Python
- Python 3.6+
- Moduli standard: `subprocess`, `os`, `sys`, `time`, `tempfile`, `shutil`, `re`, `json`, `datetime`

## 📦 Installazione

1. **Clona o scarica il repository**:
   ```bash
   git clone <repository-url>
   cd test_ubuntu
   ```

2. **Installa le dipendenze**:
   ```bash
   sudo apt install sysbench lsb-release
   ```

3. **Configura l'ambiente Python** (opzionale):
   ```bash
   python3 -m venv env
   source env/bin/activate
   ```

## 🚀 Utilizzo

### Esecuzione Base
```bash
python3 test.py
```

### Con Ambiente Virtuale
```bash
source env/bin/activate
python test.py
```

## 📊 Output

### 1. Output Console
Lo script fornisce feedback in tempo reale con emoji:

```
🏁 Avvio benchmark completo del sistema...
🔍 Controllo dipendenze...
✅ Tutte le dipendenze sono installate
📋 Raccolta informazioni di sistema...
✅ Informazioni di sistema raccolte
🚀 Inizio benchmark CPU...
   ⏱️ Esecuzione test CPU single-thread...
   ⏱️ Esecuzione test CPU multi-thread (16 cores)...
✅ Benchmark CPU completato
💾 Inizio benchmark Memoria...
   ⏱️ Esecuzione test memoria (default settings)...
   ⏱️ Esecuzione test memoria (large 5GB blocks)...
✅ Benchmark Memoria completato
💽 Inizio benchmark Disco I/O...
   📂 Preparazione file di test (5GB)...
   ⏱️ Esecuzione test lettura sequenziale (block size 1M)...
   ⏱️ Esecuzione test scrittura sequenziale (block size 1M)...
   ⏱️ Esecuzione test lettura randomica (block size 4k)...
   ⏱️ Esecuzione test scrittura randomica (block size 4k)...
   🧹 Pulizia file di test...
✅ Benchmark Disco I/O completato
📊 Generazione report finale...
```

### 2. Report Finale
```
=== BENCHMARK HOST ===
Hostname: Ubuntu-2404-noble-amd64-base
Distro: Ubuntu 24.04.3 LTS
Kernel: 6.8.0-85-generic
CPU model: AMD Ryzen 7 PRO 8700GE w/ Radeon 780M Graphics
CPU cores(logici): 16
RAM totale: 61Gi
Disk root fs: 437G (totale) / 410G (libero)

=== CPU ===
[1 thread]   total time: 10.0002s
             events/s : 6366.84
[all cores]  total time: 10.0003s
             events/s : 47877.54

=== MEMORIA ===
default run:   trasferito=98601.57 MiB, speed=9859.38 MiB/sec
large 5G run:  trasferito=5120.00 MiB, speed=43302.88 MiB/sec

=== DISCO ===
seq read : 21551.63 MiB/s
seq write: 565.78 MiB/s
rnd read : 4771.51 MiB/s
rnd write: 70.95 MiB/s

⏰ Durata totale benchmark: 75.06 secondi
🎉 Benchmark completato con successo!
```

### 3. File JSON
Il file JSON generato ha nome: `benchmark_{hostname}_{timestamp}.json`

Esempio: `benchmark_Ubuntu-2404-noble-amd64-base_20251025_175403.json`

## 📄 Struttura File JSON

```json
{
  "benchmark_info": {
    "timestamp": "2025-10-25T17:54:03.140649",
    "duration_seconds": 75.06,
    "tool_version": "sysbench_analyzer_v1.0",
    "test_date": "2025-10-25",
    "test_time": "17:54:03"
  },
  "system_info": {
    "hostname": "Ubuntu-2404-noble-amd64-base",
    "os_distribution": "Ubuntu 24.04.3 LTS",
    "kernel_version": "6.8.0-85-generic",
    "cpu_model": "AMD Ryzen 7 PRO 8700GE w/ Radeon 780M Graphics",
    "cpu_cores": 16,
    "ram_total": "61Gi",
    "disk_total": "437G",
    "disk_free": "410G"
  },
  "cpu_benchmark": {
    "single_thread": {
      "total_time_seconds": 10.0002,
      "events_per_second": 6366.84
    },
    "multi_thread": {
      "total_time_seconds": 10.0003,
      "events_per_second": 47877.54,
      "threads_used": 16
    }
  },
  "memory_benchmark": {
    "default_test": {
      "transferred": "98601.57 MiB",
      "speed_mib_per_sec": 9859.38
    },
    "large_test_5gb": {
      "transferred": "5120.00 MiB",
      "speed_mib_per_sec": 43302.88
    }
  },
  "io_benchmark": {
    "sequential_read": {
      "speed_mib_per_sec": 21551.63,
      "latency_ms": 0,
      "requests_per_sec": 21551.63,
      "block_size": "1M"
    },
    "sequential_write": {
      "speed_mib_per_sec": 565.78,
      "requests_per_sec": 565.78,
      "block_size": "1M"
    },
    "random_read": {
      "speed_mib_per_sec": 4771.51,
      "requests_per_sec": 1221505.63,
      "block_size": "4k"
    },
    "random_write": {
      "speed_mib_per_sec": 70.95,
      "requests_per_sec": 18164.39,
      "block_size": "4k"
    }
  },
  "performance_summary": {
    "cpu_single_thread_score": 6366.84,
    "cpu_multi_thread_score": 47877.54,
    "memory_bandwidth_mib_sec": 43302.88,
    "io_seq_read_mib_sec": 21551.63,
    "io_seq_write_mib_sec": 565.78,
    "io_random_read_iops": 1221505.63,
    "io_random_write_iops": 18164.39
  }
}
```

## 🔍 Interpretazione Risultati

### CPU Performance
- **Single-thread**: Eventi per secondo con 1 core
- **Multi-thread**: Eventi per secondo con tutti i core
- **Più alto = migliore**

### Memory Performance
- **Default test**: Bandwidth memoria con block 1KB
- **Large test**: Bandwidth memoria con block 1MB su 5GB
- **Più alto = migliore** (MiB/sec)

### I/O Performance
- **Sequential Read/Write**: Throughput sequenziale (MiB/s)
- **Random Read/Write**: Throughput randomico (MiB/s) e IOPS
- **Block size**: 1M per sequenziale, 4k per randomico
- **Più alto = migliore**

## 🤖 Utilizzo per Confronti LLM

Il file JSON è ottimizzato per analisi automatizzate. Un LLM può facilmente:

1. **Confrontare prestazioni** tra server diversi
2. **Identificare colli di bottiglia** confrontando le metriche
3. **Generare report comparativi** automaticamente
4. **Calcolare score compositi** basati sui benchmark

### Esempio Prompt per LLM:
```
Confronta questi due file JSON di benchmark e dimmi quale server ha prestazioni migliori:
- Server A: [inserire JSON]
- Server B: [inserire JSON]

Analizza CPU, memoria e I/O e fornisci un report dettagliato.
```

## ⚙️ Configurazione Test

### Dimensioni Test
- **CPU**: 10 secondi per test
- **Memoria**: 
  - Default: ~100GB trasferimento
  - Large: 5GB con block 1MB
- **I/O**: 5GB di file di test per ogni operazione

### Personalizzazione
Per modificare i parametri dei test, edita le funzioni nel file `test.py`:
- `bench_cpu()`: Parametri CPU
- `bench_memory()`: Parametri memoria  
- `bench_io()`: Parametri I/O

## 🔧 Troubleshooting

### Errore: Comandi mancanti
```bash
sudo apt install sysbench lsb-release
```

### Errore: Spazio disco insufficiente
Il test I/O richiede ~5GB di spazio libero temporaneo.

### Errore: Permessi
Assicurati di avere permessi di scrittura nella directory corrente.

### Performance inconsistenti
- Chiudi applicazioni pesanti durante il test
- Esegui il test più volte e fai la media
- Il sistema dovrebbe essere relativamente idle

## 📈 Tempo di Esecuzione

Il benchmark completo richiede circa **60-80 secondi**:
- Controlli iniziali: ~2s
- CPU benchmark: ~20s  
- Memory benchmark: ~25s
- I/O benchmark: ~30s (più variabile)

## 🆚 Confronto con Altri Tool

| Feature | Questo Tool | stress-ng | UnixBench | Phoronix |
|---------|-------------|-----------|-----------|----------|
| Output JSON | ✅ | ❌ | ❌ | ✅ |
| Progress Info | ✅ | ❌ | ✅ | ✅ |
| All-in-one | ✅ | ✅ | ✅ | ✅ |
| LLM Ready | ✅ | ❌ | ❌ | ❌ |
| Lightweight | ✅ | ✅ | ✅ | ❌ |

## 📝 Licenza

[Inserire informazioni licenza]

## 🤝 Contributi

Per miglioramenti e bug report, aprire issue o pull request.

## 📞 Supporto

Per supporto tecnico:
- Controllare la sezione Troubleshooting
- Aprire un issue su GitHub
- Verificare i log di output per errori specifici