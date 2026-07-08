"use client";

import { useCallback, useEffect, useState } from "react";

type Service = {
  source_type: string;
  source_service_id: string;
  title: string | null;
  summary: string | null;
  target: string | null;
  criteria: string | null;
  benefit: string | null;
  application_method: string | null;
  contact: string | null;
  links: string[];
  ministry: string | null;
  region_sido: string | null;
  region_sigungu: string | null;
  cancer_relevance: string | null;
  cancer_relevance_reason: string | null;
};

const LEVELS = [
  { key: "high", label: "관련 높음" },
  { key: "medium", label: "관련 있음" },
  { key: "low", label: "확인 필요" },
];

// 확정 표현 금지 (PRODUCT_SPEC 7장). "대상일 수 있음 / 확인 필요"만 사용한다.
function badge(level: string | null): { cls: string; text: string } {
  if (level === "high") return { cls: "high", text: "대상일 수 있음" };
  if (level === "medium") return { cls: "medium", text: "대상일 수 있음" };
  return { cls: "low", text: "확인 필요" };
}

function regionText(s: Service): string {
  if (s.source_type === "national") return "중앙부처 (전국)";
  return [s.region_sido, s.region_sigungu].filter(Boolean).join(" ") || "지역 미상";
}

export default function Home() {
  const [q, setQ] = useState("");
  const [sido, setSido] = useState("");
  const [sidoOptions, setSidoOptions] = useState<string[]>([]);
  const [levels, setLevels] = useState<string[]>(["high", "medium", "low"]);
  const [results, setResults] = useState<Service[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Service | null>(null);
  // 개발/QA 전용 표시 모드. URL에 ?debug=1 이 있을 때만 분류 근거를 화면에 보여준다.
  const [debug, setDebug] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setDebug(params.get("debug") === "1");
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (sido) params.set("sido", sido);
    if (levels.length) params.set("relevance", levels.join(","));
    params.set("limit", "100");
    try {
      const res = await fetch(`/api/services?${params.toString()}`);
      const data = await res.json();
      setResults(data.results ?? []);
      setCount(data.count ?? 0);
    } catch {
      setResults([]);
      setCount(0);
    } finally {
      setLoading(false);
    }
  }, [q, sido, levels]);

  useEffect(() => {
    // 시도 옵션 로드 (지역 필터용).
    fetch("/api/services?relevance=high,medium,low,exclude&limit=1000")
      .then((r) => r.json())
      .then((d: { results: Service[] }) => {
        const set = new Set<string>();
        (d.results ?? []).forEach((s) => {
          if (s.region_sido) set.add(s.region_sido);
        });
        setSidoOptions(Array.from(set).sort((a, b) => a.localeCompare(b, "ko")));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function toggleLevel(key: string) {
    setLevels((prev) =>
      prev.includes(key) ? prev.filter((l) => l !== key) : [...prev, key]
    );
  }

  return (
    <main className="wrap">
      <header className="site-header">
        <h1>암환우 복지 매칭</h1>
        <p className="tagline">
          중앙부처·지자체 공공 복지 정보를 암환우 관점에서 모아 봅니다.
        </p>
      </header>

      <div className="disclaimer">
        여기 표시되는 결과는 <strong>확정 판정이 아니라 참고용</strong>입니다. 실제 지원
        대상 여부와 조건은 각 제도의 소관기관에서 확인하세요.
      </div>

      <section className="filters" aria-label="검색 및 필터">
        <div className="row">
          <div className="field" style={{ flex: "2 1 260px" }}>
            <label htmlFor="q">검색어</label>
            <input
              id="q"
              type="text"
              placeholder="예: 암, 의료비, 간병, 치료비"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && load()}
            />
          </div>
          <div className="field">
            <label htmlFor="sido">지역 (시도)</label>
            <select
              id="sido"
              value={sido}
              onChange={(e) => setSido(e.target.value)}
            >
              <option value="">전체 (중앙부처 포함)</option>
              {sidoOptions.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="field">
          <label>관련성</label>
          <div className="chips" role="group" aria-label="관련성 필터">
            {LEVELS.map((lv) => (
              <button
                key={lv.key}
                type="button"
                className="chip"
                aria-pressed={levels.includes(lv.key)}
                onClick={() => toggleLevel(lv.key)}
              >
                {lv.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      <p className="result-meta">
        {loading ? "불러오는 중…" : `검색 결과 ${count}건`}
        {sido ? ` · 지역: ${sido} (+ 전국 제도)` : ""}
      </p>

      {!loading && results.length === 0 ? (
        <div className="empty">
          조건에 맞는 제도를 찾지 못했습니다. 검색어나 필터를 조정해 보세요.
        </div>
      ) : (
        <div className="list">
          {results.map((s) => {
            const b = badge(s.cancer_relevance);
            return (
              <button
                key={`${s.source_type}:${s.source_service_id}`}
                className="card"
                onClick={() => setSelected(s)}
              >
                <div className="card-top">
                  <h3>{s.title ?? "(제목 없음)"}</h3>
                  <span className={`badge ${b.cls}`}>{b.text}</span>
                </div>
                {s.summary ? <p className="summary">{s.summary}</p> : null}
                <div className="meta-row">
                  <span className="source-tag">
                    {s.source_type === "national" ? "중앙부처" : "지자체"}
                  </span>
                  <span>{regionText(s)}</span>
                  {s.ministry ? <span>{s.ministry}</span> : null}
                  {debug ? (
                    <span className="dev-tag">dev:{s.cancer_relevance}</span>
                  ) : null}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {selected ? (
        <Detail
          service={selected}
          debug={debug}
          onClose={() => setSelected(null)}
        />
      ) : null}
    </main>
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="detail-section">
      <h4>{label}</h4>
      {value ? (
        <p>{value}</p>
      ) : (
        <p className="unknown">원문에서 확인되지 않음</p>
      )}
    </div>
  );
}

function Detail({
  service,
  debug,
  onClose,
}: {
  service: Service;
  debug: boolean;
  onClose: () => void;
}) {
  const b = badge(service.cancer_relevance);
  return (
    <div className="overlay" onClick={onClose}>
      <div
        className="drawer"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <button className="drawer-close" onClick={onClose} aria-label="닫기">
          ×
        </button>
        <span className={`badge ${b.cls}`}>{b.text}</span>
        <h2>{service.title ?? "(제목 없음)"}</h2>
        <div className="meta-row">
          <span className="source-tag">
            {service.source_type === "national" ? "중앙부처" : "지자체"}
          </span>
          <span>{regionText(service)}</span>
          {service.ministry ? <span>{service.ministry}</span> : null}
        </div>

        <Field label="지원 대상" value={service.target} />
        <Field label="선정 기준" value={service.criteria} />
        <Field label="지원 내용" value={service.benefit} />
        <Field label="신청 방법" value={service.application_method} />
        <Field label="문의처" value={service.contact} />

        {service.links.length ? (
          <div className="detail-section links">
            <h4>관련 링크</h4>
            {service.links.map((l, i) => (
              <p key={i}>{l}</p>
            ))}
          </div>
        ) : null}

        <div className="note">
          이 제도는 회원님이 <strong>대상일 수 있음</strong>을 안내할 뿐이며, 확정 판정이
          아닙니다. 소득·나이·지역 등 세부 조건은 소관기관에서 <strong>확인이 필요</strong>
          합니다.
        </div>

        {/* 개발/QA 전용: ?debug=1 일 때만 분류 등급·근거를 노출한다. 일반 사용자에게는 숨긴다. */}
        {debug ? (
          <div className="dev-note">
            <strong>[개발용]</strong> 관련성 등급:{" "}
            <code>{service.cancer_relevance ?? "-"}</code>
            <br />
            분류 근거: {service.cancer_relevance_reason ?? "-"}
          </div>
        ) : null}
      </div>
    </div>
  );
}
