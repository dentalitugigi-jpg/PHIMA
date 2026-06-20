"""PHIMA Streamlit application entry point.

Dental panoramic guided interpretation and shorthand-to-report generator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import streamlit as st


TMJ_NORMAL_WORDING = (
    "Relasi kondilus, fossa, dan eminensia artikularis tampak dalam batas normal radiografis. "
    "Tidak tampak gambaran osteoartritis, remodeling patologis, maupun penebalan kortikal abnormal."
)

ABBREVIATION_EXPANSIONS: dict[str, str] = {
    "IM": "impaksi",
    "H": "horizontal",
    "M": "mesioangular",
    "D": "distoangular",
    "V": "vertikal",
    "PE": "partial erupsi",
    "B": "bersinggungan",
    "S": "superimpose",
    "PR": "pulpitis reversible",
    "PIR": "pulpitis irreversible",
    "NP": "nekrosis pulpa",
    "AP": "abses periapikal",
    "GR": "gangren radiks",
    "ED": "edentulous",
    "PG": "periodontitis generalisata",
    "TD": "tambalan sampai dentin",
    "TP": "tambalan sampai kamar pulpa",
    "DBN": "dalam batas normal radiografis",
}

TOKEN_RE = re.compile(
    r"\b(DBN|PIR|CROWDING|PE|PR|NP|AP|GR|ED|PG|TD|TP|IM|H|M|D|V|B|S)\b", re.IGNORECASE
)
TOOTH_RE = re.compile(r"\b(?:[1-4][1-8]|[5-8][1-5])\b")


@dataclass(frozen=True)
class Finding:
    """Structured radiographic finding mapped from shorthand input."""

    interpretation: str
    diagnosis: str
    suggestion: str


ABBREVIATIONS: dict[str, Finding] = {
    "IM": Finding(
        "Tampak gambaran impaksi gigi dengan posisi dan relasi terhadap struktur anatomis sekitar perlu dievaluasi.",
        "Suspek impaksi gigi.",
        "Konsultasi bedah mulut untuk penilaian kebutuhan odontektomi dan pemeriksaan lanjutan bila diperlukan.",
    ),
    "H": Finding("Arah gigi impaksi tampak horizontal.", "Impaksi gigi posisi horizontal.", "Evaluasi relasi gigi impaksi terhadap kanalis mandibularis atau sinus maksilaris."),
    "M": Finding("Arah gigi impaksi tampak mesioangular.", "Impaksi gigi posisi mesioangular.", "Evaluasi bedah mulut dan korelasi klinis."),
    "D": Finding("Arah gigi impaksi tampak distoangular.", "Impaksi gigi posisi distoangular.", "Evaluasi bedah mulut dan korelasi klinis."),
    "V": Finding("Arah gigi impaksi tampak vertikal.", "Impaksi gigi posisi vertikal.", "Evaluasi potensi erupsi dan kebutuhan perawatan."),
    "PE": Finding("Tampak partial erupsi pada gigi terkait.", "Status partial erupsi.", "Korelasi klinis terhadap jaringan lunak perikoronal."),
    "B": Finding("Tampak relasi bersinggungan dengan struktur anatomis sekitar.", "Relasi anatomis dekat/bersinggungan.", "Pertimbangkan evaluasi radiografis lanjutan bila indikatif."),
    "S": Finding("Tampak superimpose dengan struktur anatomis sekitar.", "Superimposisi radiografis.", "Pertimbangkan proyeksi atau modalitas tambahan bila diperlukan."),
    "PR": Finding("Tampak gambaran karies yang secara klinis dapat berkaitan dengan pulpitis reversible.", "Suspek pulpitis reversible.", "Evaluasi klinis, tes vitalitas, dan perawatan restoratif."),
    "PIR": Finding("Tampak gambaran karies dalam yang secara klinis dapat berkaitan dengan pulpitis irreversible.", "Suspek pulpitis irreversible.", "Evaluasi endodontik dan perawatan saluran akar bila indikatif."),
    "NP": Finding("Tampak kondisi gigi yang mengarah pada nekrosis pulpa berdasarkan temuan radiografis terkait.", "Suspek nekrosis pulpa.", "Tes vitalitas dan evaluasi endodontik."),
    "AP": Finding("Tampak gambaran radiolusen periapikal yang dapat sesuai dengan abses periapikal.", "Suspek abses periapikal.", "Evaluasi endodontik dan korelasi dengan tanda inflamasi klinis."),
    "GR": Finding("Tampak sisa akar/gangren radiks pada regio terkait.", "Suspek gangren radiks.", "Evaluasi prognosis; pertimbangkan ekstraksi bila tidak dapat dipertahankan."),
    "ED": Finding("Tampak area edentulous pada regio terkait.", "Status edentulous.", "Pertimbangkan rehabilitasi prostodontik sesuai kondisi jaringan pendukung."),
    "PG": Finding("Tampak penurunan tulang alveolar menyeluruh yang mengarah pada periodontitis generalisata.", "Suspek periodontitis generalisata.", "Pemeriksaan periodontal komprehensif dan terapi periodontal bertahap."),
    "TD": Finding("Tampak restorasi/tambalan sampai dentin pada gigi terkait.", "Status tambalan sampai dentin.", "Evaluasi adaptasi restorasi dan kontrol berkala."),
    "TP": Finding("Tampak restorasi/tambalan sampai kamar pulpa pada gigi terkait.", "Status tambalan sampai kamar pulpa.", "Evaluasi endodontik dan integritas restorasi."),
    "DBN": Finding("Struktur yang dinilai tampak dalam batas normal radiografis.", "Dalam batas normal radiografis.", "Kontrol berkala sesuai indikasi klinis."),
    "CROWDING": Finding("Tampak ketidakteraturan posisi gigi yang mengarah pada crowding dental.", "Suspek crowding dental.", "Konsultasi ortodontik untuk analisis ruang."),
}


def expand_abbreviations(text: str) -> str:
    """Expand PHIMA shorthand abbreviations while preserving user wording."""

    def replace(match: re.Match[str]) -> str:
        code = match.group(1).upper()
        if code == "CROWDING":
            return "crowding"
        return f"{code} ({ABBREVIATION_EXPANSIONS[code]})"

    return TOKEN_RE.sub(replace, text.strip())


def format_location(text: str) -> str:
    """Return a concise tooth/regio label from a shorthand fragment."""

    teeth = TOOTH_RE.findall(text)
    if teeth:
        return "gigi " + ", ".join(dict.fromkeys(teeth))
    return "regio yang dituliskan"


def parse_shorthand(shorthand: str) -> list[tuple[str, str, Finding]]:
    """Parse free-text shorthand into reportable findings for PHIMA v0.1 compatibility."""

    entries: list[tuple[str, str, Finding]] = []
    for raw_line in shorthand.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for match in TOKEN_RE.finditer(line):
            code = match.group(1).upper()
            if code == "CROWDING":
                code = "CROWDING"
            entries.append((code, format_location(line), ABBREVIATIONS[code]))
    return entries


def render_legacy_report(entries: list[tuple[str, str, Finding]]) -> dict[str, list[str]]:
    """Build legacy Indonesian radiology report sections from parsed shorthand."""

    if not entries:
        return {
            "interpretasi": ["Belum ditemukan singkatan yang dapat dikenali."],
            "diagnosis": ["Belum dapat disusun karena data shorthand belum dikenali."],
            "saran": ["Periksa kembali format input dan gunakan daftar singkatan yang tersedia."],
        }

    interpretation: list[str] = []
    diagnosis: list[str] = []
    suggestions: list[str] = []
    seen_suggestions: set[str] = set()
    for code, location, finding in entries:
        interpretation.append(f"Pada {location}: {finding.interpretation} ({ABBREVIATION_EXPANSIONS.get(code, code)})")
        diagnosis.append(f"{finding.diagnosis} Lokasi: {location}.")
        if finding.suggestion not in seen_suggestions:
            suggestions.append(finding.suggestion)
            seen_suggestions.add(finding.suggestion)
    return {"interpretasi": interpretation, "diagnosis": diagnosis, "saran": suggestions}


def formalize_stage_summary(stage_name: str, text: str, default: str) -> str:
    """Create a formal Indonesian confirmation paragraph from conversational input."""

    cleaned = expand_abbreviations(text)
    if not cleaned:
        return default
    sentences = [line.strip(" .") for line in cleaned.splitlines() if line.strip()]
    joined = "; ".join(sentences)
    return f"Berdasarkan input {stage_name}, didapatkan temuan: {joined}."


def build_final_report(stage_1: str, stage_2: str, stage_3: str) -> dict[str, str]:
    """Generate PHIMA v0.2 report sections from confirmed stage inputs."""

    teeth = expand_abbreviations(stage_1) or "Tidak terdapat temuan gigi spesifik yang dilaporkan."
    jaw = expand_abbreviations(stage_2) or "Mandibula, maksila, dan sinus maksilaris tampak dalam batas normal radiografis berdasarkan input pengguna."
    tmj_input = expand_abbreviations(stage_3)
    tmj = tmj_input or TMJ_NORMAL_WORDING

    legacy_entries = parse_shorthand("\n".join([stage_1, stage_2, stage_3]))
    legacy = render_legacy_report(legacy_entries)

    return {
        "Jumlah Gigi": f"Jumlah dan distribusi gigi dinilai berdasarkan sistem penomoran FDI. {teeth}",
        "Mahkota dan Akar": f"Evaluasi mahkota dan akar menunjukkan: {teeth}",
        "Mandibula, Maksila, dan Sinus Maksilaris": jaw,
        "TMJ": tmj,
        "Alveolar Crest": "Alveolar crest dievaluasi pada seluruh regio; temuan spesifik mengikuti catatan pengguna. " + jaw,
        "Periapikal": "Daerah periapikal dievaluasi pada gigi terkait. " + teeth,
        "Kesan": " ".join(legacy["diagnosis"]) if legacy_entries else "Kesan radiografis disusun berdasarkan temuan terkonfirmasi pada tahap gigi, rahang-sinus, dan TMJ.",
        "Saran": " ".join(legacy["saran"]) if legacy_entries else "Korelasikan dengan pemeriksaan klinis, tes vitalitas, pemeriksaan periodontal, dan pemeriksaan penunjang lain sesuai indikasi.",
        "Suspek Radiodiagnosis": " ".join(legacy["diagnosis"]) if legacy_entries else "Tidak terdapat suspek radiodiagnosis spesifik dari shorthand yang dikenali; tinjau ulang bersama temuan klinis.",
        "Disclaimer": "Laporan ini merupakan draf berbasis input pengguna dan tidak menggantikan interpretasi final dokter gigi/radiolog kedokteran gigi. Temuan harus dikorelasikan dengan pemeriksaan klinis, riwayat pasien, kualitas citra, serta pemeriksaan penunjang lain bila diperlukan.",
    }


st.set_page_config(page_title="PHIMA v0.2 Dental Report Generator", page_icon="🦷", layout="wide")

st.markdown(
    """
    <style>
    :root { --phima-navy: #0B1F3A; --phima-gold: #D4A017; --phima-gold-hover: #B88913; --phima-white: #FFFFFF; }
    .stApp { background: var(--phima-white); }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, var(--phima-navy) 0%, #102B4F 100%); }
    [data-testid="stSidebar"] * { color: var(--phima-white) !important; }
    [data-testid="stSidebar"] code { color: var(--phima-navy) !important; background-color: rgba(255, 255, 255, 0.92) !important; }
    .phima-hero { background: linear-gradient(135deg, var(--phima-navy) 0%, #14345F 100%); border-radius: 24px; padding: 2.25rem 2.5rem; margin-bottom: 1.75rem; box-shadow: 0 18px 45px rgba(11, 31, 58, 0.16); border: 1px solid rgba(212, 160, 23, 0.35); }
    .phima-eyebrow { color: var(--phima-gold); font-size: 0.85rem; font-weight: 800; letter-spacing: 0.18em; margin-bottom: 0.65rem; text-transform: uppercase; }
    .phima-title { color: var(--phima-white); font-size: clamp(2.35rem, 5vw, 4.4rem); font-weight: 900; line-height: 0.95; margin: 0; }
    .phima-subtitle { color: rgba(255, 255, 255, 0.88); font-size: 1.08rem; max-width: 860px; margin-top: 0.9rem; }
    .phima-card { border: 1px solid rgba(11, 31, 58, 0.12); border-left: 6px solid var(--phima-gold); border-radius: 18px; padding: 1.1rem 1.25rem; background: #fffdf8; margin: 1rem 0; }
    .phima-stage { color: var(--phima-navy); font-weight: 900; }
    div[data-testid="stButton"] { display: flex; justify-content: center; margin: 1.2rem 0 1.1rem; }
    div[data-testid="stButton"] > button { background-color: var(--phima-gold) !important; color: var(--phima-white) !important; border: 0 !important; border-radius: 999px !important; min-height: 3.7rem; min-width: min(100%, 360px); padding: 0.9rem 2.2rem !important; font-size: 1.05rem !important; font-weight: 800 !important; letter-spacing: 0.02em; box-shadow: 0 14px 28px rgba(212, 160, 23, 0.28); transition: background-color 160ms ease, box-shadow 160ms ease, transform 160ms ease; }
    div[data-testid="stButton"] > button:hover { background-color: var(--phima-gold-hover) !important; color: var(--phima-white) !important; box-shadow: 0 18px 34px rgba(184, 137, 19, 0.34); transform: translateY(-1px); }
    div[data-testid="stButton"] > button:focus, div[data-testid="stButton"] > button:active { color: var(--phima-white) !important; border: 0 !important; box-shadow: 0 0 0 0.18rem rgba(212, 160, 23, 0.32), 0 14px 28px rgba(212, 160, 23, 0.28) !important; }
    </style>
    <section class="phima-hero"><div class="phima-eyebrow">Dental Radiology Platform · v0.2</div><h1 class="phima-title">PHIMA</h1><div class="phima-subtitle">Workflow interpretasi radiografi panoramik bertahap dengan konfirmasi percakapan, tanpa dropdown.</div></section>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("PHIMA v0.2")
    st.write("Gunakan input teks bebas dan sistem penomoran gigi FDI.")
    st.divider()
    st.subheader("Ekspansi Singkatan")
    for code, meaning in ABBREVIATION_EXPANSIONS.items():
        st.markdown(f"- **{code}** = {meaning}")

for key, initial in {"stage_1_confirmed": False, "stage_2_visible": False, "stage_2_confirmed": False, "stage_3_visible": False}.items():
    st.session_state.setdefault(key, initial)

st.markdown("""
<div class="phima-card"><strong>Instruksi:</strong> Isi tiap tahap dengan bahasa klinis singkat atau shorthand PHIMA. Setelah tiap input, lakukan konfirmasi untuk melihat ringkasan formal sebelum melanjutkan.</div>
""", unsafe_allow_html=True)

st.markdown('<h2 class="phima-stage">STAGE 1 — GIGI</h2>', unsafe_allow_html=True)
st.caption("Masukkan temuan: jumlah gigi, gigi hilang/edentulous, impaksi, karies PR/PIR, nekrosis pulpa, gangren radiks, abses periapikal, tambalan TD/TP, crowding/diastema, dan periodontal findings.")
stage_1 = st.text_area("Input temuan gigi", height=170, placeholder="Contoh: Jumlah gigi 28. 18 IM H PE B kanalis. 36 PIR AP. 46 TD. ED 14, 15. PG ringan.", key="stage_1")
if st.button("Konfirmasi Tahap 1", type="primary"):
    st.session_state.stage_1_confirmed = True
if st.session_state.stage_1_confirmed:
    st.subheader("Konfirmasi Temuan Gigi")
    st.success(formalize_stage_summary("gigi", stage_1, "Pada struktur gigi tidak terdapat temuan spesifik yang dilaporkan."))
    if st.button("Lanjut Tahap 2", type="primary"):
        st.session_state.stage_2_confirmed = False
        st.session_state.stage_3_visible = False
        st.session_state.stage_2_visible = True

if st.session_state.get("stage_2_visible"):
    st.markdown('<h2 class="phima-stage">STAGE 2 — MANDIBULA, MAKSILA, SINUS MAKSILARIS</h2>', unsafe_allow_html=True)
    st.caption("Masukkan temuan: mandibula, maksila, sinus maksilaris, kanalis mandibularis, alveolar crest, lesi tulang, dan relasi akar gigi impaksi dengan sinus atau kanalis.")
    stage_2 = st.text_area("Input temuan mandibula, maksila, dan sinus maksilaris", height=170, placeholder="Contoh: Mandibula dan maksila DBN. Sinus maksilaris kanan-kiri DBN. Akar 18 superimpose dengan sinus maksilaris.", key="stage_2")
    if st.button("Konfirmasi Tahap 2", type="primary"):
        st.session_state.stage_2_confirmed = True
    if st.session_state.stage_2_confirmed:
        st.subheader("Konfirmasi Temuan Mandibula, Maksila, dan Sinus Maksilaris")
        st.success(formalize_stage_summary("mandibula, maksila, dan sinus maksilaris", stage_2, "Mandibula, maksila, sinus maksilaris, kanalis mandibularis, alveolar crest, dan struktur tulang yang dilaporkan tampak dalam batas normal radiografis."))
        if st.button("Lanjut Tahap 3", type="primary"):
            st.session_state.stage_3_visible = True

if st.session_state.get("stage_3_visible"):
    st.markdown('<h2 class="phima-stage">STAGE 3 — TMJ</h2>', unsafe_allow_html=True)
    st.caption("Masukkan temuan: kondilus kanan, kondilus kiri, posisi/asimetri kondilus, relasi kondilus-fossa-eminensia, osteoartritis, remodeling patologis, dan cortical thickening.")
    stage_3 = st.text_area("Input temuan TMJ", value=TMJ_NORMAL_WORDING, height=160, key="stage_3")
    if st.button("Generate Final PHIMA Report", type="primary"):
        st.session_state.final_report = build_final_report(stage_1, st.session_state.get("stage_2", ""), stage_3)

if "final_report" in st.session_state:
    st.header("Final PHIMA Report")
    for section, content in st.session_state.final_report.items():
        st.subheader(section)
        st.write(content)

with st.expander("PHIMA v0.1 shorthand generator tetap tersedia"):
    sample = "18 IM H PE\n36 AP NP\n46 PR\nPG Crowding"
    shorthand = st.text_area("Shorthand input v0.1", value=sample, height=140, key="legacy_shorthand")
    if st.button("Interpretasi Panoramik v0.1", type="primary"):
        report = render_legacy_report(parse_shorthand(shorthand))
        st.subheader("Interpretasi Radiografis")
        for item in report["interpretasi"]:
            st.markdown(f"- {item}")
        st.subheader("Suspek Radiodiagnosis")
        for item in report["diagnosis"]:
            st.markdown(f"- {item}")
        st.subheader("Saran")
        for item in report["saran"]:
            st.markdown(f"- {item}")
