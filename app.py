"""PHIMA Streamlit application entry point.

Dental panoramic guided interpretation and shorthand-to-report generator.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


APP_VERSION_LABEL = "PHIMA v0.3.1 — Auto-Save Final Report Workflow"
DATABASE_PATH = Path("phima_bank_data.sqlite3")


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
        return f"Temuan: {default}"
    sentences = [line.strip(" .") for line in cleaned.splitlines() if line.strip()]
    joined = "; ".join(sentences)
    return f"Temuan: {joined}."


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


def format_report_text(report: dict[str, str]) -> str:
    """Return a plain-text PHIMA report suitable for editing, copying, and saving."""

    return "\n\n".join(f"{section}\n{content}" for section, content in report.items())


def set_report_status(status: str) -> None:
    """Persist the visible radiologist correction workflow status."""

    st.session_state.report_status = status


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp for PHIMA database records."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def report_hash(report_text: str) -> str:
    """Return a stable hash used to prevent duplicate final-report saves."""

    return hashlib.sha256(report_text.encode("utf-8")).hexdigest()


def init_cases_table() -> None:
    """Create or migrate the PHIMA cases table used by the auto-save workflow."""

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                user_name TEXT,
                report_template TEXT,
                stage_1_findings TEXT,
                stage_2_findings TEXT,
                stage_3_findings TEXT,
                generated_ai_report TEXT,
                final_corrected_report TEXT,
                radiodiagnosis TEXT,
                notes TEXT,
                report_status TEXT NOT NULL
            )
            """
        )
        existing_columns = {row[1] for row in connection.execute("PRAGMA table_info(cases)")}
        required_columns = {
            "case_id": "TEXT PRIMARY KEY",
            "created_at": "TEXT",
            "updated_at": "TEXT",
            "user_name": "TEXT",
            "report_template": "TEXT",
            "stage_1_findings": "TEXT",
            "stage_2_findings": "TEXT",
            "stage_3_findings": "TEXT",
            "generated_ai_report": "TEXT",
            "final_corrected_report": "TEXT",
            "radiodiagnosis": "TEXT",
            "notes": "TEXT",
            "report_status": "TEXT",
        }
        for column, definition in required_columns.items():
            if column not in existing_columns and column != "case_id":
                connection.execute(f"ALTER TABLE cases ADD COLUMN {column} {definition}")


def save_case_to_database() -> bool:
    """Insert or update the current case when the final corrected report is ready."""

    final_report = st.session_state.get("corrected_report_text", "")
    current_hash = report_hash(final_report)
    if st.session_state.get("last_saved_final_report_hash") == current_hash:
        return False

    init_cases_table()
    now = utc_timestamp()
    case_id = st.session_state.setdefault("case_id", str(uuid.uuid4()))
    created_at = st.session_state.setdefault("case_created_at", now)
    payload = {
        "case_id": case_id,
        "created_at": created_at,
        "updated_at": now,
        "user_name": st.session_state.get("user_name", ""),
        "report_template": st.session_state.get("report_template", "Panoramic Radiology Report"),
        "stage_1_findings": st.session_state.get("stage_1", ""),
        "stage_2_findings": st.session_state.get("stage_2", ""),
        "stage_3_findings": st.session_state.get("stage_3", ""),
        "generated_ai_report": st.session_state.get("generated_ai_report_original", st.session_state.get("ai_report_text", "")),
        "final_corrected_report": final_report,
        "radiodiagnosis": st.session_state.get("radiodiagnosis", ""),
        "notes": st.session_state.get("case_notes", ""),
        "report_status": "Final Report Ready",
    }
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            INSERT INTO cases (
                case_id, created_at, updated_at, user_name, report_template,
                stage_1_findings, stage_2_findings, stage_3_findings, generated_ai_report,
                final_corrected_report, radiodiagnosis, notes, report_status
            ) VALUES (
                :case_id, :created_at, :updated_at, :user_name, :report_template,
                :stage_1_findings, :stage_2_findings, :stage_3_findings, :generated_ai_report,
                :final_corrected_report, :radiodiagnosis, :notes, :report_status
            )
            ON CONFLICT(case_id) DO UPDATE SET
                updated_at=excluded.updated_at,
                user_name=excluded.user_name,
                report_template=excluded.report_template,
                stage_1_findings=excluded.stage_1_findings,
                stage_2_findings=excluded.stage_2_findings,
                stage_3_findings=excluded.stage_3_findings,
                generated_ai_report=excluded.generated_ai_report,
                final_corrected_report=excluded.final_corrected_report,
                radiodiagnosis=excluded.radiodiagnosis,
                notes=excluded.notes,
                report_status=excluded.report_status
            """,
            payload,
        )
    st.session_state.last_saved_final_report_hash = current_hash
    st.session_state.last_saved_at = now
    return True


init_cases_table()
st.set_page_config(page_title="P.H.I.M.A. Radiology Report Platform", page_icon="🦷", layout="wide")

st.markdown(
    """
    <style>
    :root { --phima-navy: #061426; --phima-blue: #0B1F3A; --phima-gold: #D4A017; --phima-gold-hover: #F0B92D; --phima-white: #FFFFFF; --phima-ink: #EAF2FF; --phima-muted: #B9C7DA; --phima-green-bg: rgba(14, 86, 55, 0.94); --phima-green-border: #31D782; --phima-green-text: #C8FFD9; }
    .stApp { background: radial-gradient(circle at top left, rgba(21, 62, 110, 0.6), transparent 34rem), linear-gradient(180deg, #061426 0%, #081A30 42%, #06101F 100%); color: var(--phima-ink); }
    .block-container { padding-top: 2.2rem; max-width: 1180px; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #061426 0%, #0B1F3A 55%, #0E2B4A 100%); border-right: 1px solid rgba(212, 160, 23, 0.28); }
    [data-testid="stSidebar"] * { color: var(--phima-white) !important; }
    [data-testid="stSidebar"] code { color: var(--phima-navy) !important; background-color: rgba(255, 255, 255, 0.92) !important; }
    .phima-hero { background: linear-gradient(135deg, rgba(6, 20, 38, 0.98) 0%, rgba(13, 47, 86, 0.96) 56%, rgba(7, 26, 48, 0.98) 100%); border-radius: 30px; padding: 3rem 3.2rem; margin-bottom: 2rem; box-shadow: 0 26px 70px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.08); border: 1px solid rgba(212, 160, 23, 0.42); position: relative; overflow: hidden; }
    .phima-hero::after { content: ""; position: absolute; inset: auto -8rem -11rem auto; width: 26rem; height: 26rem; background: radial-gradient(circle, rgba(212,160,23,0.28), transparent 68%); }
    .phima-eyebrow { color: var(--phima-gold); font-size: 0.98rem; font-weight: 900; letter-spacing: 0.22em; margin-bottom: 0.8rem; text-transform: uppercase; }
    .phima-title { color: var(--phima-white); font-size: clamp(3.2rem, 6vw, 6.2rem); font-weight: 950; line-height: 0.95; margin: 0; letter-spacing: 0.08em; text-shadow: 0 12px 32px rgba(0,0,0,0.32); }
    .phima-subtitle { color: rgba(255, 255, 255, 0.94); font-size: clamp(1.4rem, 2.2vw, 2rem); font-weight: 750; max-width: 940px; margin-top: 1.05rem; }
    .phima-tagline { color: var(--phima-gold); font-size: clamp(1.06rem, 1.55vw, 1.32rem); font-weight: 800; margin-top: 0.65rem; letter-spacing: 0.02em; }
    .phima-card { border: 1px solid rgba(212, 160, 23, 0.32); border-left: 7px solid var(--phima-gold); border-radius: 22px; padding: 1.45rem 1.65rem; background: rgba(9, 28, 51, 0.86); margin: 1.2rem 0 1.6rem; box-shadow: 0 18px 48px rgba(0,0,0,0.22); font-size: 1.18rem; line-height: 1.65; color: var(--phima-ink); }
    .phima-stage { color: var(--phima-white); padding: 1rem 1.35rem; margin: 2.1rem 0 1rem; border-radius: 22px; background: linear-gradient(135deg, rgba(11,31,58,0.96), rgba(18,58,100,0.88)); border: 1px solid rgba(212,160,23,0.36); box-shadow: 0 18px 42px rgba(0,0,0,0.28); text-align: center; }
    .phima-stage-kicker { display: block; font-size: clamp(1.32rem, 2.1vw, 2.05rem); font-weight: 750; line-height: 1.15; letter-spacing: 0.02em; }
    .phima-stage-title { display: block; margin-top: 0.28rem; font-size: clamp(1.58rem, 2.45vw, 2.28rem); font-weight: 950; line-height: 1.1; letter-spacing: 0.045em; }
    .phima-description { color: #D9E7F8; font-size: clamp(1.28rem, 1.7vw, 1.55rem); line-height: 1.65; font-weight: 650; margin: 0.7rem 0 1rem; }
    label, .stTextArea label, [data-testid="stMarkdownContainer"] p, .stMarkdown { font-size: 1.08rem; }
    textarea { font-size: 1.1rem !important; line-height: 1.6 !important; border-radius: 18px !important; }
    div[data-testid="stAlert"] { background: var(--phima-green-bg) !important; border: 1px solid var(--phima-green-border) !important; border-radius: 22px !important; padding: 1.35rem 1.55rem !important; box-shadow: 0 18px 44px rgba(0, 0, 0, 0.28); }
    div[data-testid="stAlert"] * { color: var(--phima-green-text) !important; font-size: 1.2rem !important; line-height: 1.65 !important; font-weight: 750 !important; }
    div[data-testid="stButton"] { display: flex; justify-content: center; margin: 1.35rem 0 1.25rem; }
    div[data-testid="stButton"] > button { background: linear-gradient(135deg, var(--phima-gold) 0%, #E7B438 100%) !important; color: #071426 !important; border: 0 !important; border-radius: 18px !important; min-height: 4.15rem; min-width: min(100%, 390px); padding: 1.05rem 2.55rem !important; font-size: 1.18rem !important; font-weight: 900 !important; letter-spacing: 0.02em; box-shadow: 0 16px 32px rgba(212, 160, 23, 0.34); transition: background 160ms ease, box-shadow 160ms ease, transform 160ms ease, filter 160ms ease; }
    div[data-testid="stButton"] > button:hover { background: linear-gradient(135deg, var(--phima-gold-hover) 0%, #FFD36A 100%) !important; color: #061426 !important; box-shadow: 0 22px 42px rgba(240, 185, 45, 0.42); transform: translateY(-3px); filter: saturate(1.12); }
    div[data-testid="stButton"] > button:focus, div[data-testid="stButton"] > button:active { color: #061426 !important; border: 0 !important; box-shadow: 0 0 0 0.2rem rgba(212, 160, 23, 0.34), 0 16px 32px rgba(212, 160, 23, 0.34) !important; }
    h1, h2, h3, .stHeader { color: var(--phima-white) !important; }
    </style>
    <section class="phima-hero"><div class="phima-eyebrow">Premium Dental Radiology Platform · PHIMA v0.3.1 — Auto-Save Final Report Workflow</div><h1 class="phima-title">P.H.I.M.A.</h1><div class="phima-subtitle">Panoramic Hybrid Intelligence for Maxillofacial Assessment</div><div class="phima-tagline">From Panoramic Findings to Professional Radiology Reports</div></section>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header(APP_VERSION_LABEL)
    st.write("Gunakan input teks bebas dan sistem penomoran gigi FDI.")
    st.text_input("User name", key="user_name", placeholder="Nama radiolog / operator")
    st.selectbox("Selected template", ["Panoramic Radiology Report", "Impaction Assessment", "Periodontal Assessment", "TMJ Screening"], key="report_template")
    st.divider()
    st.subheader("Ekspansi Singkatan")
    for code, meaning in ABBREVIATION_EXPANSIONS.items():
        st.markdown(f"- **{code}** = {meaning}")

for key, initial in {"stage_1_confirmed": False, "stage_2_visible": False, "stage_2_confirmed": False, "stage_3_visible": False}.items():
    st.session_state.setdefault(key, initial)

st.markdown("""
<div class="phima-card"><strong>Instruksi:</strong> Isi tiap tahap menggunakan bahasa klinis singkat atau ekspansi singkatan radiologi yang sesuai. Setelah tiap input, lakukan konfirmasi untuk melihat ringkasan formal sebelum melanjutkan.</div>
""", unsafe_allow_html=True)

st.markdown('<h2 class="phima-stage"><span class="phima-stage-kicker">Konfirmasi Tahap 1</span><span class="phima-stage-title">GIGI</span></h2>', unsafe_allow_html=True)
st.markdown('<div class="phima-description">Masukkan temuan radiografis mengenai jumlah dan distribusi gigi, area edentulous, impaksi, karies PR/PIR, nekrosis pulpa, gangren radiks, abses periapikal, restorasi TD/TP, crowding/diastema, serta status periodontal.</div>', unsafe_allow_html=True)
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
    st.markdown('<h2 class="phima-stage"><span class="phima-stage-kicker">Konfirmasi Tahap 2</span><span class="phima-stage-title">MANDIBULA • MAKSILA • SINUS MAKSILARIS</span></h2>', unsafe_allow_html=True)
    st.markdown('<div class="phima-description">Masukkan temuan radiografis pada mandibula, maksila, sinus maksilaris, kanalis mandibularis, alveolar crest, lesi tulang, serta hubungan gigi impaksi terhadap struktur anatomi sekitar.</div>', unsafe_allow_html=True)
    stage_2 = st.text_area("Input temuan mandibula, maksila, dan sinus maksilaris", height=170, placeholder="Contoh: Mandibula dan maksila DBN. Sinus maksilaris kanan-kiri DBN. Akar 18 superimpose dengan sinus maksilaris.", key="stage_2")
    if st.button("Konfirmasi Tahap 2", type="primary"):
        st.session_state.stage_2_confirmed = True
    if st.session_state.stage_2_confirmed:
        st.subheader("Konfirmasi Temuan Mandibula, Maksila, dan Sinus Maksilaris")
        st.success(formalize_stage_summary("mandibula, maksila, dan sinus maksilaris", stage_2, "Mandibula, maksila, sinus maksilaris, kanalis mandibularis, alveolar crest, dan struktur tulang yang dilaporkan tampak dalam batas normal radiografis."))
        if st.button("Lanjut Tahap 3", type="primary"):
            st.session_state.stage_3_visible = True

if st.session_state.get("stage_3_visible"):
    st.markdown('<h2 class="phima-stage"><span class="phima-stage-kicker">Konfirmasi Tahap 3</span><span class="phima-stage-title">TMJ</span></h2>', unsafe_allow_html=True)
    st.markdown('<div class="phima-description">Masukkan evaluasi radiografis TMJ meliputi kondilus kanan dan kiri, posisi atau asimetri kondilus, relasi kondilus-fossa-eminensia, osteoartritis, remodeling patologis, serta penebalan kortikal.</div>', unsafe_allow_html=True)
    stage_3 = st.text_area("Input temuan TMJ", value=TMJ_NORMAL_WORDING, height=160, key="stage_3")
    if st.button("Generate Final PHIMA Report", type="primary"):
        st.session_state.ai_report = build_final_report(stage_1, st.session_state.get("stage_2", ""), stage_3)
        st.session_state.ai_report_text = format_report_text(st.session_state.ai_report)
        st.session_state.generated_ai_report_original = st.session_state.ai_report_text
        st.session_state.corrected_report_text = st.session_state.ai_report_text
        st.session_state.final_corrected_report = st.session_state.corrected_report_text
        st.session_state.ai_report_editor = st.session_state.ai_report_text
        st.session_state.corrected_report_editor = st.session_state.corrected_report_text
        set_report_status("Draft AI Report")

if "ai_report_text" in st.session_state:
    st.header("Radiologist Correction Workflow")
    st.text_area(
        "Generated AI Report",
        value=st.session_state.get("generated_ai_report_original", st.session_state.get("ai_report_text", "")),
        height=260,
        disabled=True,
        help="Original AI-generated draft saved separately from the final corrected report.",
    )

    corrected_report_text = st.text_area(
        "Final Corrected Report",
        height=360,
        key="corrected_report_editor",
        help="Primary final report field for copying and future saving.",
    )
    st.session_state.corrected_report_text = corrected_report_text
    if corrected_report_text != st.session_state.get("final_corrected_report", ""):
        st.session_state.final_corrected_report = corrected_report_text
        if st.session_state.get("last_saved_final_report_hash") != report_hash(corrected_report_text):
            set_report_status("Corrected by Radiologist")


    status = st.session_state.get("report_status", "Draft AI Report")
    status_steps = ["Draft AI Report", "Corrected by Radiologist", "Final Report Ready"]
    status_markup = "".join(
        f'<span style="display:inline-block;margin:0.25rem 0.4rem 0.25rem 0;padding:0.55rem 0.9rem;border-radius:999px;border:1px solid rgba(212,160,23,0.48);background:{"rgba(212,160,23,0.24)" if step == status else "rgba(255,255,255,0.06)"};color:#EAF2FF;font-weight:850;">{step}</span>'
        for step in status_steps
    )
    st.markdown(f'<div class="phima-card"><strong>Status:</strong><br>{status_markup}</div>', unsafe_allow_html=True)

    st.text_input("Suspek Radiodiagnosis", key="radiodiagnosis", placeholder="Ringkasan radiodiagnosis untuk database dan analytics")
    st.text_area("Notes", key="case_notes", height=110, placeholder="Catatan internal tambahan")

    col_ready, col_copy = st.columns(2)
    with col_ready:
        if st.button("Final Report Ready", type="primary"):
            st.session_state.final_corrected_report = st.session_state.corrected_report_text
            set_report_status("Final Report Ready")
            saved = save_case_to_database()
            if saved:
                st.success("Final report ready and automatically saved to PHIMA Bank Data.")
            else:
                st.info("Final report is already saved to PHIMA Bank Data. Edit the Final Corrected Report to update the saved case.")
    with col_copy:
        final_report_for_copy = st.session_state.get("final_corrected_report", st.session_state.corrected_report_text)
        st.download_button(
            "Copy Final Report",
            data=final_report_for_copy,
            file_name="phima_final_corrected_report.txt",
            mime="text/plain",
            type="primary",
            help="Uses the final corrected report as the main output for copying and future saving.",
        )
        components.html(
            f"""
            <button id=\"copy-final-report\" style=\"width:100%;min-height:3.4rem;border:0;border-radius:18px;background:linear-gradient(135deg,#D4A017 0%,#E7B438 100%);color:#071426;font-size:1.05rem;font-weight:900;cursor:pointer;\">Copy Final Report to Clipboard</button>
            <div id=\"copy-status\" style=\"margin-top:0.55rem;color:#C8FFD9;font-weight:700;text-align:center;\"></div>
            <script>
            const report = {final_report_for_copy!r};
            const button = document.getElementById('copy-final-report');
            const status = document.getElementById('copy-status');
            button.addEventListener('click', async () => {{
              try {{
                await navigator.clipboard.writeText(report);
                status.textContent = 'Final Report Ready';
              }} catch (error) {{
                status.textContent = 'Clipboard unavailable. Use the download copy above.';
              }}
            }});
            </script>
            """,
            height=105,
        )

    if st.session_state.get("final_corrected_report"):
        st.subheader("Main Output: Final Corrected Report")
        st.text(st.session_state.final_corrected_report)

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
