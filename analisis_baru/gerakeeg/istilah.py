"""Terminologi baku metode baru. Semua keluaran memakai istilah ini."""

# label timestamp → nama gerakan
GERAKAN = {"N": "Ngeed", "AKA": "Agem Kanan", "AKI": "Agem Kiri"}
URUTAN_GERAKAN = ["Ngeed", "Agem Kanan", "Agem Kiri"]

# fase per repetisi, berurutan. "Gerak" = fase pembuka yang dinamai sesuai gerakannya (Ngeed/Agem Kanan/Agem Kiri)
FASE_REPETISI = ["Gerak", "Tahan", "Naik", "Berdiri"]
TUTUP_MATA = "Tutup Mata"
BUKA_MATA = "Buka Mata"         # Romberg mata terbuka (label BM), sebelum Tutup Mata
ISTIRAHAT = "Istirahat"          # jeda panjang antar-blok; TURUNAN (tidak ada timestamp), dipakai sebagai acuan
URUTAN_FASE = FASE_REPETISI + [BUKA_MATA, TUTUP_MATA, ISTIRAHAT]

LABEL_FASE = {"Gerak": "Gerak (Ngeed/Agem)", "Tahan": "Tahan", "Naik": "Naik", "Berdiri": "Berdiri",
              BUKA_MATA: "Buka Mata", TUTUP_MATA: "Tutup Mata", ISTIRAHAT: "Istirahat*"}

# 16 kanal EEG KT88; kiri direferensikan ke A1, kanan ke A2 (telinga ipsilateral)
KIRI = ["Fp1", "F3", "C3", "P3", "O1", "F7", "T3", "T5"]
KANAN = ["Fp2", "F4", "C4", "P4", "O2", "F8", "T4", "T6"]
KANAL = KIRI + KANAN
BELAHAN = {**{c: "kiri (A1)" for c in KIRI}, **{c: "kanan (A2)" for c in KANAN}}
