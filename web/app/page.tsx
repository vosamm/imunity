"use client";

import { useCallback, useEffect, useRef, useState } from "react";

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
  support_categories: string[];
  cancer_relevance: string | null;
  cancer_relevance_reason: string | null;
  similarity?: number;
};

const LEVELS = [
  { key: "high", label: "관련 높음" },
  { key: "medium", label: "관련 있음" },
  { key: "low", label: "확인 필요" },
];

// schema.SUPPORT_CATEGORIES와 1:1 (이름 변경 시 양쪽 함께).
const CATEGORIES = [
  "의료비", "생계", "돌봄·간병", "심리지원", "이동·교통", "주거", "현물·물품",
];

// 카테고리별 글리프 — 사진이 없는 복지 데이터의 카드 리듬을 위한 최소 시각 요소.
const GLYPHS: Record<string, string> = {
  의료비: "💊", 생계: "🪙", "돌봄·간병": "🤝", 심리지원: "💬",
  "이동·교통": "🚗", 주거: "🏠", "현물·물품": "🎁",
};

const PAGE_SIZE = 30;

// 확정 표현 금지 (PRODUCT_SPEC 7장). "대상일 수 있음 / 확인 필요"만 사용한다.
function badge(level: string | null): { cls: string; text: string } {
  if (level === "high") return { cls: "high", text: "대상일 수 있음" };
  if (level === "medium") return { cls: "medium", text: "대상일 수 있음" };
  return { cls: "low", text: "확인 필요" };
}

function regionText(s: Service): string {
  if (s.source_type === "national") return "전국";
  return [s.region_sido, s.region_sigungu].filter(Boolean).join(" ") || "지역 미상";
}

function keyOf(s: Service): string {
  return `${s.source_type}:${s.source_service_id}`;
}

function glyphOf(s: Service): string {
  return GLYPHS[s.support_categories[0]] ?? "🏥";
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"
      strokeLinecap="round" aria-hidden="true">
      <circle cx="11" cy="11" r="7" /><path d="m20 20-3.2-3.2" />
    </svg>
  );
}

function HeartIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      aria-hidden="true">
      <path d="M12 20.5C6.5 16.5 3 13.2 3 9.2 3 6.6 5 4.7 7.4 4.7c1.6 0 3 .8 3.9 2 .9-1.2 2.3-2 3.9-2C18.6 4.7 21 6.6 21 9.2c0 4-3.5 7.3-9 11.3Z" />
    </svg>
  );
}

export default function Home() {
  // 탭 상태
  const [tab, setTab] = useState<"keyword" | "ai">("keyword");

  // 키워드 검색 탭 state
  const [q, setQ] = useState("");
  const [sido, setSido] = useState("");
  const [sigungu, setSigungu] = useState("");
  const [category, setCategory] = useState("");
  const [sidoOptions, setSidoOptions] = useState<string[]>([]);
  const [sigunguOptions, setSigunguOptions] = useState<string[]>([]);
  const [levels, setLevels] = useState<string[]>(["high", "medium", "low"]);
  const [results, setResults] = useState<Service[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  // AI 매칭 탭 전용 state
  const [aiAge, setAiAge] = useState("");
  const [aiCancerType, setAiCancerType] = useState("");
  const [aiSido, setAiSido] = useState("");
  const [aiSigungu, setAiSigungu] = useState("");
  const [aiIncomeLevel, setAiIncomeLevel] = useState("");
  const [aiFreeText, setAiFreeText] = useState("");
  const [aiResults, setAiResults] = useState<Service[]>([]);
  const [aiTotal, setAiTotal] = useState(0);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const [aiSigunguOptions, setAiSigunguOptions] = useState<string[]>([]);

  const [selected, setSelected] = useState<Service | null>(null);
  // 저장(하트) — 클라이언트 표시 상태. Airbnb 위시리스트 하트의 번역.
  const [saved, setSaved] = useState<Set<string>>(new Set());
  // 상세를 연 카드로 포커스를 되돌리기 위한 참조 (키보드 사용자 배려).
  const lastCardRef = useRef<HTMLElement | null>(null);
  // 개발/QA 전용 표시 모드. URL에 ?debug=1 이 있을 때만 분류 근거를 화면에 보여준다.
  const [debug, setDebug] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setDebug(params.get("debug") === "1");
  }, []);

  const buildParams = useCallback(
    (offset: number) => {
      const params = new URLSearchParams();
      if (q.trim()) params.set("q", q.trim());
      if (sido) params.set("sido", sido);
      if (sigungu) params.set("sigungu", sigungu);
      if (category) params.set("category", category);
      if (levels.length) params.set("relevance", levels.join(","));
      params.set("limit", String(PAGE_SIZE));
      if (offset > 0) params.set("offset", String(offset));
      return params;
    },
    [q, sido, sigungu, category, levels]
  );

  // 검색 조건 변경 → 첫 페이지 재조회 (타이핑 부담을 줄이려 300ms 디바운스).
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/services?${buildParams(0).toString()}`);
        const data = await res.json();
        if (cancelled) return;
        setResults(data.results ?? []);
        setTotal(data.total ?? 0);
      } catch {
        if (!cancelled) {
          setResults([]);
          setTotal(0);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [buildParams]);

  // 시도 옵션 로드.
  useEffect(() => {
    fetch("/api/regions")
      .then((r) => r.json())
      .then((d: { sido: string[] }) => setSidoOptions(d.sido ?? []))
      .catch(() => {});
  }, []);

  // 시도 변경 → 시군구 옵션 갱신, 기존 시군구 선택 해제.
  useEffect(() => {
    setSigungu("");
    if (!sido) {
      setSigunguOptions([]);
      return;
    }
    fetch(`/api/regions?sido=${encodeURIComponent(sido)}`)
      .then((r) => r.json())
      .then((d: { sigungu: string[] }) => setSigunguOptions(d.sigungu ?? []))
      .catch(() => setSigunguOptions([]));
  }, [sido]);

  // AI 탭: 시도 변경 → 시군구 옵션 갱신.
  useEffect(() => {
    setAiSigungu("");
    if (!aiSido) {
      setAiSigunguOptions([]);
      return;
    }
    fetch(`/api/regions?sido=${encodeURIComponent(aiSido)}`)
      .then((r) => r.json())
      .then((d: { sigungu: string[] }) => setAiSigunguOptions(d.sigungu ?? []))
      .catch(() => setAiSigunguOptions([]));
  }, [aiSido]);

  async function loadMore() {
    setLoadingMore(true);
    try {
      const res = await fetch(
        `/api/services?${buildParams(results.length).toString()}`
      );
      const data = await res.json();
      setResults((prev) => [...prev, ...(data.results ?? [])]);
      setTotal(data.total ?? total);
    } catch {
      // 더보기 실패는 기존 결과 유지
    } finally {
      setLoadingMore(false);
    }
  }

  function toggleLevel(key: string) {
    setLevels((prev) =>
      prev.includes(key) ? prev.filter((l) => l !== key) : [...prev, key]
    );
  }

  function resetFilters() {
    setQ("");
    setSido("");
    setSigungu("");
    setCategory("");
    setLevels(["high", "medium", "low"]);
  }

  function openDetail(s: Service, cardEl: HTMLElement) {
    lastCardRef.current = cardEl;
    setSelected(s);
  }

  function closeDetail() {
    setSelected(null);
    // 열었던 카드로 포커스 복귀 (키보드/스크린리더 사용자).
    lastCardRef.current?.focus();
  }

  function toggleSave(k: string) {
    setSaved((prev) => {
      const next = new Set(prev);
      next.has(k) ? next.delete(k) : next.add(k);
      return next;
    });
  }

  async function handleAiSearch() {
    setAiLoading(true);
    setAiError("");
    try {
      const resp = await fetch("/api/rag-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          form: {
            age: aiAge ? parseInt(aiAge, 10) : null,
            cancer_type: aiCancerType || null,
            region_sido: aiSido || null,
            region_sigungu: aiSigungu || null,
            income_level: aiIncomeLevel || null,
          },
          free_text: aiFreeText || null,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        setAiError(err.error ?? "매칭 중 문제가 생겼습니다. 잠시 후 다시 시도해 주세요.");
        setAiResults([]);
        setAiTotal(0);
        return;
      }
      const data = await resp.json();
      setAiResults(data.results ?? []);
      setAiTotal(data.total ?? 0);
    } catch {
      setAiError("AI 매칭 서버에 연결할 수 없습니다. rag_server.py가 실행 중인지 확인하세요.");
      setAiResults([]);
      setAiTotal(0);
    } finally {
      setAiLoading(false);
    }
  }

  const hasActiveFilter =
    q.trim() || sido || sigungu || category || levels.length !== 3;

  function renderCard(s: Service, showSim: boolean) {
    const b = badge(s.cancer_relevance);
    const k = keyOf(s);
    const isSaved = saved.has(k);
    return (
      <div
        key={k}
        className="card"
        role="button"
        tabIndex={0}
        onClick={(e) => openDetail(s, e.currentTarget)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            openDetail(s, e.currentTarget);
          }
        }}
      >
        <div className="card-plate">
          <span className="card-glyph" aria-hidden="true">{glyphOf(s)}</span>
          <button
            type="button"
            className="heart"
            aria-pressed={isSaved}
            aria-label={isSaved ? "저장 해제" : "저장"}
            onClick={(e) => {
              e.stopPropagation();
              toggleSave(k);
            }}
          >
            <HeartIcon />
          </button>
        </div>
        <h3>{s.title ?? "(제목 없음)"}</h3>
        {s.summary ? <p className="summary">{s.summary}</p> : null}
        <p className="card-region">
          <span className="source-tag">
            {s.source_type === "national" ? "중앙부처" : "지자체"}
          </span>
          · {regionText(s)}
        </p>
        <div className="card-foot">
          <span className={`badge ${b.cls}`}>{b.text}</span>
          {s.support_categories.slice(0, 2).map((c) => (
            <span key={c} className="cat-tag">{c}</span>
          ))}
          {showSim && s.similarity != null ? (
            <span className="similarity">{Math.round(s.similarity * 100)}% 일치</span>
          ) : null}
          {debug ? <span className="dev-tag">dev:{s.cancer_relevance}</span> : null}
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="topnav">
        <div className="brand">
          <svg className="brand-mark" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 21.3c-.4 0-.8-.15-1.1-.45C7 17 3.2 13.6 3.2 9.4 3.2 6.4 5.4 4.2 8.2 4.2c1.5 0 2.9.7 3.8 1.9.9-1.2 2.3-1.9 3.8-1.9 2.8 0 5 2.2 5 5.2 0 4.2-3.8 7.6-7.7 11.45-.3.3-.7.45-1.1.45Z" />
          </svg>
          imunity
        </div>
        <nav className="nav-tabs" role="tablist" aria-label="검색 방식">
          <button
            role="tab"
            aria-selected={tab === "keyword"}
            className="nav-tab"
            onClick={() => setTab("keyword")}
          >
            <svg className="tab-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7" /><path d="m20 20-3.2-3.2" />
            </svg>
            <span className="tab-label">키워드 검색</span>
          </button>
          <button
            role="tab"
            aria-selected={tab === "ai"}
            className="nav-tab"
            onClick={() => setTab("ai")}
          >
            <svg className="tab-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 3.5 13.6 9l5.4 1.6-5.4 1.6L12 17.7l-1.6-5.5L5 10.6 10.4 9 12 3.5Z" />
              <path d="M18.5 4v3M20 5.5h-3" />
            </svg>
            <span className="tab-label">AI 매칭</span>
          </button>
        </nav>
        <div className="nav-right">
          <span className="nav-note">참고용 안내 · 확정 판정 아님</span>
        </div>
      </header>

      <main>
        {tab === "keyword" && (
          <>
            <section className="hero">
              <h1 className="hero-title">암환우를 위한 복지, 한 곳에서 찾아보세요</h1>
              <p className="hero-sub">
                중앙부처와 지자체의 공공 복지를 암환우 관점에서 모았습니다. 지역과 필요를
                고르면 해당될 수 있는 제도를 보여드려요.
              </p>

              <form className="searchbar" onSubmit={(e) => e.preventDefault()}>
                <div className="search-seg">
                  <label htmlFor="q">무엇을 찾으세요</label>
                  <input
                    id="q"
                    type="text"
                    placeholder="암, 의료비, 간병, 치료비"
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                  />
                </div>
                <div className="search-seg">
                  <label htmlFor="sido">지역</label>
                  <select id="sido" value={sido} onChange={(e) => setSido(e.target.value)}>
                    <option value="">전국 (중앙부처 포함)</option>
                    {sidoOptions.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <div className="search-seg">
                  <label htmlFor="sigungu">세부 지역</label>
                  <select
                    id="sigungu"
                    value={sigungu}
                    onChange={(e) => setSigungu(e.target.value)}
                    disabled={!sido || sigunguOptions.length === 0}
                  >
                    <option value="">{sido ? "전체" : "지역 먼저 선택"}</option>
                    {sigunguOptions.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <button className="search-orb" type="submit" aria-label="검색">
                  <SearchIcon />
                </button>
              </form>

              <div className="filter-bar">
                <div className="filter-group">
                  <span className="group-label">어떤 도움이 필요하세요?</span>
                  <div className="chips" role="group" aria-label="지원 목적 필터">
                    {CATEGORIES.map((cat) => (
                      <button
                        key={cat}
                        type="button"
                        className="chip"
                        aria-pressed={category === cat}
                        onClick={() => setCategory((prev) => (prev === cat ? "" : cat))}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="filter-group">
                  <span className="group-label">관련성</span>
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
              </div>
            </section>

            <section className="results">
              <div className="results-head" role="status" aria-live="polite">
                {loading ? (
                  <span className="count-unit">불러오는 중…</span>
                ) : (
                  <>
                    <span className="count-num">{total.toLocaleString("ko-KR")}</span>
                    <span className="count-unit">개 제도</span>
                    <span className="count-sub">
                      {results.length < total ? `${results.length}개 표시 중` : "모두 표시"}
                      {sido ? ` · ${sido}${sigungu ? ` ${sigungu}` : ""} (+ 전국)` : ""}
                      {category ? ` · ${category}` : ""}
                    </span>
                  </>
                )}
              </div>

              {!loading && results.length === 0 ? (
                <div className="empty">
                  <p className="empty-title">조건에 맞는 제도를 찾지 못했습니다.</p>
                  <p className="empty-hint">
                    검색어를 줄이거나 필터를 풀면 더 많은 제도가 보입니다.
                  </p>
                  {hasActiveFilter ? (
                    <button type="button" className="reset-btn" onClick={resetFilters}>
                      필터 모두 초기화
                    </button>
                  ) : null}
                </div>
              ) : (
                <>
                  <div className="card-grid">
                    {results.map((s) => renderCard(s, false))}
                  </div>
                  {results.length < total ? (
                    <button
                      type="button"
                      className="load-more"
                      onClick={loadMore}
                      disabled={loadingMore}
                    >
                      {loadingMore ? "불러오는 중…" : `더 보기 (${results.length}/${total})`}
                    </button>
                  ) : null}
                </>
              )}
            </section>
          </>
        )}

        {tab === "ai" && (
          <>
            <section className="hero">
              <h1 className="hero-title">상황을 알려주시면 맞을 만한 제도를 찾아드려요</h1>
              <p className="hero-sub">
                나이·암 종류·지역·상황을 입력하면, 의미가 비슷한 제도를 AI가 찾아 유사도 순으로
                보여드립니다.
              </p>

              <div className="ai-card">
                <div className="ai-grid">
                  <div className="field">
                    <label htmlFor="ai-age">나이</label>
                    <input id="ai-age" type="number" placeholder="45"
                      value={aiAge} onChange={(e) => setAiAge(e.target.value)} />
                  </div>
                  <div className="field">
                    <label htmlFor="ai-cancer">암 종류</label>
                    <input id="ai-cancer" type="text" placeholder="유방암, 폐암"
                      value={aiCancerType} onChange={(e) => setAiCancerType(e.target.value)} />
                  </div>
                  <div className="field">
                    <label htmlFor="ai-sido">지역</label>
                    <select id="ai-sido" value={aiSido} onChange={(e) => setAiSido(e.target.value)}>
                      <option value="">전국</option>
                      {sidoOptions.map((s) => (<option key={s} value={s}>{s}</option>))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="ai-sigungu">세부 지역</label>
                    <select id="ai-sigungu" value={aiSigungu}
                      onChange={(e) => setAiSigungu(e.target.value)}
                      disabled={!aiSido || aiSigunguOptions.length === 0}>
                      <option value="">{aiSido ? "전체" : "지역 먼저 선택"}</option>
                      {aiSigunguOptions.map((s) => (<option key={s} value={s}>{s}</option>))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="ai-income">소득 수준</label>
                    <select id="ai-income" value={aiIncomeLevel}
                      onChange={(e) => setAiIncomeLevel(e.target.value)}>
                      <option value="">선택 안 함</option>
                      <option value="기초생활">기초생활</option>
                      <option value="차상위">차상위</option>
                      <option value="일반">일반</option>
                    </select>
                  </div>
                  <div className="field full">
                    <label htmlFor="ai-text">추가 상황</label>
                    <textarea id="ai-text" rows={3}
                      placeholder="예: 치료비가 부담되고 간병인이 필요합니다"
                      value={aiFreeText} onChange={(e) => setAiFreeText(e.target.value)} />
                  </div>
                </div>
                <button type="button" className="btn-primary"
                  onClick={handleAiSearch} disabled={aiLoading}>
                  {aiLoading ? "찾는 중…" : "맞는 제도 찾기"}
                </button>
              </div>
            </section>

            {aiError && <div className="ai-error" role="alert">{aiError}</div>}

            <section className="results">
              {aiLoading ? (
                <div className="results-head">
                  <span className="count-unit">AI가 맞는 제도를 찾고 있어요…</span>
                </div>
              ) : aiTotal > 0 ? (
                <>
                  <div className="results-head">
                    <span className="count-num">{aiTotal.toLocaleString("ko-KR")}</span>
                    <span className="count-unit">개 제도를 찾았어요</span>
                    <span className="count-sub">유사도 높은 순</span>
                  </div>
                  <div className="card-grid">
                    {aiResults.map((s) => renderCard(s, true))}
                  </div>
                </>
              ) : null}
            </section>
          </>
        )}
      </main>

      <footer className="site-footer">
        <div className="footer-inner">
          <p className="footer-disclaimer">
            여기 표시되는 결과는 <strong>확정 판정이 아니라 참고용</strong>입니다. 실제 지원
            대상 여부와 조건은 각 제도의 소관기관에서 확인하세요.
          </p>
          <span className="footer-legal">© 2026 imunity · 공공데이터포털 기반</span>
        </div>
      </footer>

      {selected ? (
        <Detail service={selected} debug={debug} onClose={closeDetail} />
      ) : null}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="detail-section">
      <h4>{label}</h4>
      {value ? <p>{value}</p> : <p className="unknown">원문에서 확인되지 않음</p>}
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
  const closeRef = useRef<HTMLButtonElement | null>(null);

  // 드로어가 열리면 닫기 버튼으로 포커스 이동, ESC로 닫기 (접근성).
  useEffect(() => {
    closeRef.current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="overlay" onClick={onClose}>
      <div
        className="drawer"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={service.title ?? "제도 상세"}
      >
        <button ref={closeRef} className="drawer-close" onClick={onClose} aria-label="닫기">
          ×
        </button>
        <h2>{service.title ?? "(제목 없음)"}</h2>
        <div className="card-foot">
          <span className={`badge ${b.cls}`}>{b.text}</span>
          <span className="source-tag">
            {service.source_type === "national" ? "중앙부처" : "지자체"}
          </span>
          <span className="cat-tag">{regionText(service)}</span>
          {service.ministry ? <span className="cat-tag">{service.ministry}</span> : null}
          {service.support_categories.map((c) => (
            <span key={c} className="cat-tag">{c}</span>
          ))}
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

        {/* 개발/QA 전용: ?debug=1 일 때만 분류 등급·근거를 노출한다. */}
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
