import React, { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { History, MessageSquarePlus, Send, ThumbsDown, ThumbsUp, Trash2 } from "lucide-react";
import api from "../api/client";
import { useLanguage } from "../i18n/LanguageContext";
import LoadingSpinner from "./LoadingSpinner";

const CHAT_STORAGE_PREFIX = "ankurai_ai_chats_v1";
const MAX_SAVED_CHATS = 12;

function currentOwnerKey() {
  try {
    const user = JSON.parse(localStorage.getItem("smart_crop_user") || "{}");
    return String(user.id || user.email || "anonymous");
  } catch {
    return "anonymous";
  }
}

function makeChat(title = "New chat", messages = []) {
  return { id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, title, updatedAt: new Date().toISOString(), messages };
}

function AskAiAssistant({ context }) {
  const { language, t, tv } = useLanguage();
  const storageKey = `${CHAT_STORAGE_PREFIX}:${currentOwnerKey()}`;
  const welcome = t("ai.welcome", "Ask me about your crop recommendation, irrigation, disease result, market support, or next farm steps.");
  const [conversations, setConversations] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || "[]");
      if (Array.isArray(saved) && saved.length) return saved.slice(0, MAX_SAVED_CHATS);
    } catch { /* Start a clean local chat if stored data is unavailable. */ }
    return [makeChat("New chat", [{ role: "assistant", content: welcome }])];
  });
  const [activeChatId, setActiveChatId] = useState(() => conversations[0]?.id);
  const [messages, setMessages] = useState(() => conversations[0]?.messages || [{ role: "assistant", content: welcome }]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [retryKind, setRetryKind] = useState("chat");
  const [feedbackSent, setFeedbackSent] = useState({});
  const [marketInfo, setMarketInfo] = useState(null);

  const messagesListRef = useRef(null);
  const requestControllerRef = useRef(null);

  useEffect(() => () => requestControllerRef.current?.abort(), []);

  useEffect(() => {
    try { localStorage.setItem(storageKey, JSON.stringify(conversations.slice(0, MAX_SAVED_CHATS))); } catch { /* Storage may be unavailable or full. */ }
  }, [conversations, storageKey]);

  useEffect(() => {
    setConversations((current) => current.map((chat) => chat.id === activeChatId ? { ...chat, messages, updatedAt: new Date().toISOString() } : chat));
  }, [activeChatId, messages]);

  const latestCrop = context?.result?.crop || context?.latestCrop || "";
  const activeChat = conversations.find((chat) => chat.id === activeChatId) || conversations[0];

  useEffect(() => {
    if (!latestCrop || !context?.selectedState) { setMarketInfo(null); return undefined; }
    const controller = new AbortController();
    setMarketInfo(null);
    api.get("/api/market/overview", {
      params: { state: context.selectedState, season: context.selectedSeason || "Auto", crop: latestCrop },
      timeout: 14000, signal: controller.signal,
    }).then((response) => {
      const value = response.data || {};
      setMarketInfo({
        crop: value.crop || latestCrop,
        season: value.season || context.selectedSeason || "Auto",
        mandi: {
          source: value.mandi?.source,
          scope: value.mandi?.scope,
          state: value.mandi?.state || context.selectedState,
          is_live: Boolean(value.mandi?.is_live),
          from_cache: Boolean(value.mandi?.from_cache),
          fetched_at: value.mandi?.fetched_at,
          records: (value.mandi?.records || []).slice(0, 5).map(({ market, district, modal_price, arrival_date }) => ({ market, district, modal_price, arrival_date })),
        },
        msp: { value: value.msp?.value, marketing_season: value.msp?.marketing_season, source: value.msp?.source },
      });
    }).catch(() => { if (!controller.signal.aborted) setMarketInfo(null); });
    return () => controller.abort();
  }, [context?.selectedSeason, context?.selectedState, latestCrop]);

  const beginNewChat = () => {
    if (requestControllerRef.current) requestControllerRef.current.abort();
    const chat = makeChat(t("ai.newChat", "New chat"), [{ role: "assistant", content: welcome }]);
    setConversations((current) => [chat, ...current].slice(0, MAX_SAVED_CHATS));
    setActiveChatId(chat.id);
    setMessages(chat.messages);
    setInput(""); setError(""); setLoading(false); setFeedbackSent({});
  };

  const selectChat = (chat) => {
    if (loading && requestControllerRef.current) requestControllerRef.current.abort();
    setActiveChatId(chat.id); setMessages(chat.messages); setError(""); setLoading(false); setFeedbackSent({});
  };

  const clearChatHistory = () => {
    if (requestControllerRef.current) requestControllerRef.current.abort();
    const chat = makeChat(t("ai.newChat", "New chat"), [{ role: "assistant", content: welcome }]);
    setConversations([chat]); setActiveChatId(chat.id); setMessages(chat.messages);
    setInput(""); setError(""); setLoading(false); setFeedbackSent({});
  };

  const quickPrompts = [
    t(
      "ai.quickExplain",
      "Explain my crop recommendation in simple words."
    ),
    t(
      "ai.quickWeek",
      "What should I do this week for this crop?"
    ),
    t(
      "ai.quickRisks",
      "What risks should I watch for in this season?"
    ),
    t(
      "ai.quickLanguage",
      "Explain this advisory in the selected language."
    ),
  ];

  const contextSummary = useMemo(
    () => [
      {
        label: t("farmer.state", "State"),
        value: tv(
          "states",
          context?.selectedState || "-"
        ),
      },
      {
        label: t("farmer.season", "Season"),
        value: tv(
          "seasons",
          context?.selectedSeason || "-"
        ),
      },
      {
        label: t("farmer.crop", "Crop"),
        value: latestCrop
          ? tv("crops", latestCrop)
          : "-",
      },
      {
        label: t(
          "cropCard.confidence",
          "Confidence"
        ),
        value:
          context?.result?.confidence !== undefined &&
          context?.result?.confidence !== null
            ? `${Number(
                context.result.confidence <= 1
                  ? context.result.confidence * 100
                  : context.result.confidence
              ).toFixed(1)}%`
            : "-",
      },
      ...(context?.form?.ph ? [{ label: t("ai.soilPh", "Soil pH"), value: context.form.ph }] : []),
      ...(context?.form?.N || context?.form?.P || context?.form?.K ? [{ label: t("ai.npk", "N-P-K inputs"), value: [context.form.N, context.form.P, context.form.K].map((value) => value || "-").join(" · ") }] : []),
      ...(context?.form?.rainfall ? [{ label: t("farmer.rainfall", "Rainfall"), value: `${context.form.rainfall} mm` }] : []),
      ...(context?.result?.irrigation ? [{ label: t("farmer.irrigation", "Irrigation estimate"), value: `${context.result.irrigation}` }] : []),
      ...(marketInfo?.mandi?.records?.length ? [{ label: t("ai.marketSnapshot", "Market snapshot"), value: `${marketInfo.mandi.records.length} · ${marketInfo.mandi.source || "AGMARKNET"}${marketInfo.mandi.is_live ? ` · ${t("market.liveUpdated", "Live data")}` : ` · ${t("market.referenceFallback", "Reference data")}`}` }] : []),
    ],
    [context, latestCrop, marketInfo, t, tv]
  );

  const sendMessage = async (text, retry = false) => {
    const question = String(text || input).trim();

    if (!question || loading) {
      return;
    }
    setConversations((current) => current.map((chat) => chat.id === activeChatId && chat.title === t("ai.newChat", "New chat")
      ? { ...chat, title: question.slice(0, 48) }
      : chat));

    const baseMessages = retry && messages[messages.length - 1]?.role === "assistant" ? messages.slice(0, -1) : messages;
    const nextMessages = retry ? baseMessages : [...baseMessages, { role: "user", content: question }];
    const historyMessages = retry ? baseMessages.slice(0, -1) : messages;
    const assistantId = `reply-${Date.now()}`;
    let controller;

    setMessages([...nextMessages, { id: assistantId, role: "assistant", content: "", streaming: true }]);
    setInput("");
    setError("");
    setRetryKind("chat");
    let timeoutId;

    try {
      setLoading(true);

      controller = new AbortController();
      requestControllerRef.current = controller;
      timeoutId = window.setTimeout(() => controller.abort(), 90000);
      const token = localStorage.getItem("smart_crop_token");
      const response = await fetch(`${String(api.defaults.baseURL || "").replace(/\/$/, "")}/api/ai/chat/stream`, {
        method: "POST", signal: controller.signal,
        headers: { "Content-Type": "application/json", Accept: "text/event-stream", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ message: question, language, context: { ...context, ...(marketInfo ? { market: marketInfo } : {}) }, history: historyMessages.filter((item) => item.role === "user" || item.content).slice(-8) }),
      });
      if (!response.ok) {
        let body = {};
        try { body = await response.json(); } catch { /* Keep the translated fallback below. */ }
        throw new Error(body.error || t("ai.failed", "AI assistant could not answer right now."));
      }
      if (!response.body) throw new Error(t("ai.failed", "AI assistant could not answer right now."));
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let completed = false;
      const handleEvent = (block) => {
        const dataLine = block.split("\n").find((line) => line.startsWith("data:"));
        if (!dataLine) return;
        let event;
        try { event = JSON.parse(dataLine.slice(5).trim()); } catch { return; }
        if (event.type === "meta") setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, contextUsed: event.context_used || [] } : item));
        if (event.type === "delta") setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, content: item.content + event.text } : item));
        if (event.type === "done") completed = true;
        if (event.type === "error") throw new Error(event.error || t("ai.failed", "AI assistant could not answer right now."));
      };
      try {
        while (true) {
          const { value, done } = await reader.read();
          buffer += decoder.decode(value || new Uint8Array(), { stream: !done }).replace(/\r/g, "");
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop() || "";
          blocks.forEach(handleEvent);
          if (done) break;
        }
        if (buffer.trim()) handleEvent(buffer);
      } finally {
        reader.releaseLock();
      }
      setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, streaming: false } : item));
      if (!completed) throw new Error(t("ai.failed", "AI assistant could not answer right now."));
      setError("");
    } catch (err) {
      const stopped = err.name === "AbortError";
      setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, streaming: false, interrupted: true } : item));
      if (!stopped) { setRetryKind("chat"); setError(err.message || t("ai.failed", "AI assistant could not answer right now.")); }
    } finally {
      if (timeoutId) window.clearTimeout(timeoutId);
      if (requestControllerRef.current === controller) {
        requestControllerRef.current = null;
        setLoading(false);
      }
    }
  };

  const rateAnswer = async (messageId, rating) => {
    setError("");
    try {
      await api.post("/api/ai/feedback", { rating, category: "general" });
      setFeedbackSent((current) => ({ ...current, [messageId]: rating }));
      setMessages((current) => current.map((message) => message.id === messageId ? { ...message, feedback: rating } : message));
    } catch {
      setRetryKind("feedback");
      setError(t("ai.feedbackFailed", "Could not save feedback. Please try again."));
    }
  };

  useEffect(() => {
    const list = messagesListRef.current;

    if (!list) {
      return;
    }

    requestAnimationFrame(() => {
      list.scrollTo({
        top: list.scrollHeight,
        behavior: "auto",
      });
    });
  }, [messages, loading]);

  return (
    <section className="surface-card flex min-w-0 flex-col overflow-hidden p-0 xl:h-[min(96dvh,1200px)] xl:min-h-[820px]">
      {/* Header */}
      <div className="flex shrink-0 flex-col gap-4 border-b border-surface-border bg-surface-muted p-4 sm:p-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <span className="section-badge">
            {t(
              "ai.badge",
              "Farm Assistant"
            )}
          </span>

          <h2 className="mt-1 text-xl font-semibold text-text-heading sm:text-2xl">
            {t("ai.title", "Ask AI")}
          </h2>

          <p className="mt-1 hidden max-w-2xl text-sm leading-6 text-text-muted sm:block">
            {t(
              "ai.subtitle",
              "Ask follow-up questions about the current recommendation. The answer uses your latest crop, irrigation, soil, season, and state context."
            )}
          </p>
        </div>
        <div className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_auto] lg:w-[min(100%,28rem)]">
          <label className="sr-only" htmlFor="ai-chat-title">{t("ai.renameChat", "Chat name")}</label>
          <input id="ai-chat-title" className="field-shell" value={activeChat?.title || ""} maxLength={60} onChange={(event) => setConversations((current) => current.map((chat) => chat.id === activeChatId ? { ...chat, title: event.target.value } : chat))} />
          <button type="button" className="theme-button-primary gap-2 px-3" onClick={beginNewChat}><MessageSquarePlus size={16} aria-hidden="true" />{t("ai.newChat", "New chat")}</button>
        </div>
      </div>

      {/* Main content */}
      <div className="grid w-full min-w-0 flex-1 grid-cols-1 gap-3 p-3 sm:p-4 xl:min-h-0 xl:grid-cols-[minmax(190px,0.22fr)_minmax(0,1fr)] xl:grid-rows-[minmax(0,1fr)]">
        {/* Context / quick questions */}
        <aside className="surface-card-soft order-2 min-w-0 p-4 xl:order-1 xl:h-full xl:min-h-0 xl:overflow-y-auto">
          <p className="text-sm font-semibold text-text-heading">
            {t(
              "ai.contextTitle",
              "Current context"
            )}
          </p>

          <div className="mt-4 grid gap-3">
            {contextSummary.map((item) => (
              <div
                key={item.label}
                className="rounded-md border border-surface-border bg-surface-card p-3"
              >
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-text-subtle">
                  {item.label}
                </p>

                <p className="mt-1 text-sm font-semibold text-accent-800">
                  {item.value}
                </p>
              </div>
            ))}
          </div>

          {/* Quick questions */}
          <div className="mt-4 space-y-2">
            <p className="text-sm font-semibold text-text-heading">
              {t(
                "ai.quickTitle",
                "Quick questions"
              )}
            </p>

            {quickPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => sendMessage(prompt)}
                disabled={loading}
                className="w-full rounded-md border border-surface-border bg-surface-card px-3 py-2.5 text-left text-sm leading-5 text-text-muted transition-colors hover:border-primary-300 hover:text-primary-800 disabled:opacity-60"
              >
                {prompt}
              </button>
            ))}
          </div>

          <div className="mt-5 border-t border-surface-border pt-4">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-text-heading">{t("ai.chatHistory", "Recent chats")}</p>
              <button type="button" className="inline-flex min-h-10 items-center gap-1 text-xs font-semibold text-text-muted hover:text-danger-700" onClick={clearChatHistory} title={t("ai.clearHistory", "Clear chat history")}><Trash2 size={14} aria-hidden="true" />{t("ai.clearHistory", "Clear")}</button>
            </div>
            <div className="mt-2 space-y-1">
              {conversations.map((chat) => <button key={chat.id} type="button" onClick={() => selectChat(chat)} aria-current={chat.id === activeChatId ? "true" : undefined} className={`block min-h-10 w-full truncate rounded-md border px-3 py-2 text-left text-sm ${chat.id === activeChatId ? "border-primary-300 bg-primary-50 font-semibold text-primary-800" : "border-transparent text-text-muted hover:border-surface-border hover:bg-surface-card"}`}>{chat.title || t("ai.newChat", "New chat")}</button>)}
            </div>
            <p className="mt-2 text-xs leading-5 text-text-subtle">{t("ai.localHistory", "Chat history is saved only on this device and account profile.")}</p>
          </div>
        </aside>

        {/* AI chat */}
        <div className="surface-card-soft order-1 flex min-h-[82dvh] min-w-0 flex-col p-3 sm:min-h-[86dvh] sm:p-4 xl:order-2 xl:h-full xl:min-h-0">
          <div className="mb-3 flex shrink-0 items-center gap-2 xl:hidden">
            <History size={16} className="shrink-0 text-text-muted" aria-hidden="true" />
            <label className="sr-only" htmlFor="ai-mobile-chat-history">{t("ai.chatHistory", "Recent chats")}</label>
            <select id="ai-mobile-chat-history" className="theme-select min-h-10 flex-1" value={activeChatId || ""} onChange={(event) => { const selected = conversations.find((chat) => chat.id === event.target.value); if (selected) selectChat(selected); }}>
              {conversations.map((chat) => <option key={chat.id} value={chat.id}>{chat.title || t("ai.newChat", "New chat")}</option>)}
            </select>
          </div>
          <div
            ref={messagesListRef}
            className="theme-scrollbar min-h-0 min-w-0 flex-1 space-y-4 overflow-x-hidden overflow-y-auto overscroll-contain pr-1 sm:pr-2 [overflow-anchor:none]"
          >
            {messages.map((message, index) => {
              const isUser = message.role === "user";

              return (
                <div
                  key={`${message.role}-${index}`}
                  className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
                >
                  <div
                    className={[
                      "min-w-0 max-w-[94%] break-words rounded-lg px-4 py-3 text-sm leading-6 sm:max-w-[86%] sm:px-5 sm:py-4 sm:text-[0.9375rem]",
                      isUser
                        ? "bg-primary-700 text-white"
                        : "border border-surface-border bg-white text-text-heading shadow-sm",
                    ].join(" ")}
                  >
                    {isUser ? (
                      /* User messages stay as normal text */
                      <span className="whitespace-pre-wrap">
                        {message.content}
                      </span>
                    ) : (
                      /* AI messages are rendered as Markdown */
                      <div className="ai-markdown min-w-0 [overflow-wrap:anywhere]">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            h1: ({ children }) => (
                              <h1 className="mb-3 mt-2 text-lg font-bold leading-6 text-text-heading">
                                {children}
                              </h1>
                            ),

                            h2: ({ children }) => (
                              <h2 className="mb-3 mt-4 text-base font-bold leading-6 text-text-heading">
                                {children}
                              </h2>
                            ),

                            h3: ({ children }) => (
                              <h3 className="mb-2 mt-4 text-sm font-bold leading-6 text-text-heading">
                                {children}
                              </h3>
                            ),

                            p: ({ children }) => (
                              <p className="mb-3 last:mb-0">
                                {children}
                              </p>
                            ),

                            ul: ({ children }) => (
                              <ul className="mb-3 ml-5 list-disc space-y-1">
                                {children}
                              </ul>
                            ),

                            ol: ({ children }) => (
                              <ol className="mb-3 ml-5 list-decimal space-y-1">
                                {children}
                              </ol>
                            ),

                            li: ({ children }) => (
                              <li className="pl-1">
                                {children}
                              </li>
                            ),

                            strong: ({ children }) => (
                              <strong className="font-bold text-text-heading">
                                {children}
                              </strong>
                            ),

                            em: ({ children }) => (
                              <em className="italic">
                                {children}
                              </em>
                            ),

                            blockquote: ({
                              children,
                            }) => (
                              <blockquote className="my-3 border-l-4 border-accent-300 pl-4 italic text-text-muted">
                                {children}
                              </blockquote>
                            ),

                            code: ({
                              children,
                            }) => (
                              <code className="rounded bg-surface-soft px-1.5 py-0.5 text-xs font-mono">
                                {children}
                              </code>
                            ),

                            pre: ({ children }) => (
                              <pre className="my-3 overflow-x-auto rounded-xl bg-surface-soft p-3 text-xs leading-5">
                                {children}
                              </pre>
                            ),

                            hr: () => (
                              <hr className="my-4 border-surface-border" />
                            ),

                            a: ({
                              href,
                              children,
                            }) => (
                              <a
                                href={href}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-medium text-accent-700 underline underline-offset-2 hover:text-accent-900"
                              >
                                {children}
                              </a>
                            ),

                            table: ({
                              children,
                            }) => (
                              <div className="my-3 overflow-x-auto">
                                <table className="min-w-full border-collapse text-sm">
                                  {children}
                                </table>
                              </div>
                            ),

                            thead: ({
                              children,
                            }) => (
                              <thead className="bg-surface-soft">
                                {children}
                              </thead>
                            ),

                            th: ({ children }) => (
                              <th className="border border-surface-border px-3 py-2 text-left font-semibold">
                                {children}
                              </th>
                            ),

                            td: ({ children }) => (
                              <td className="border border-surface-border px-3 py-2">
                                {children}
                              </td>
                            ),
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    )}
                    {!isUser && message.contextUsed?.length ? <div className="mt-3 border-t border-surface-border pt-2"><p className="text-[11px] font-semibold text-text-subtle">{t("ai.contextUsed", "App data included")}</p><div className="mt-1 flex flex-wrap gap-1">{message.contextUsed.map((source) => <span key={source} className="status-chip status-info">{t(`ai.source.${source}`, source.split("_").join(" "))}</span>)}</div></div> : null}
                    {!isUser && message.interrupted ? <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-warning-700"><span>{t("ai.interrupted", "Response stopped or interrupted.")}</span>{!error ? <button type="button" className="font-semibold underline" onClick={() => { const question = [...messages].reverse().find((item) => item.role === "user")?.content; if (question) sendMessage(question, true); }}>{t("ai.retry", "Retry")}</button> : null}</div> : null}
                  </div>
                  {!isUser && message.id && message.content && !message.streaming ? <div className="mt-1 flex items-center gap-1 pl-2" aria-label={t("ai.rateAnswer", "Rate this answer")}>
                    <button type="button" disabled={Boolean(message.feedback || feedbackSent[message.id])} onClick={() => rateAnswer(message.id, "helpful")} className="inline-flex min-h-8 items-center gap-1 text-xs text-text-subtle hover:text-primary-700 disabled:text-primary-700" aria-label={t("ai.helpful", "Helpful")}><ThumbsUp size={14} aria-hidden="true" />{message.feedback === "helpful" || feedbackSent[message.id] === "helpful" ? t("ai.thanks", "Thanks") : null}</button>
                    <button type="button" disabled={Boolean(message.feedback || feedbackSent[message.id])} onClick={() => rateAnswer(message.id, "not_helpful")} className="inline-flex min-h-8 items-center text-text-subtle hover:text-danger-700 disabled:text-danger-700" aria-label={t("ai.notHelpful", "Not helpful")}><ThumbsDown size={14} aria-hidden="true" /></button>
                  </div> : null}
                </div>
              );
            })}

            {/* Loading */}
            {loading ? (
              <div className="pt-2">
                <LoadingSpinner
                  label={t(
                    "ai.thinking",
                    "Preparing an answer..."
                  )}
                />
                <button type="button" onClick={() => requestControllerRef.current?.abort()} className="theme-button-ghost mt-2 min-h-9 px-3 py-2 text-xs">{t("ai.stop", "Stop response")}</button>
              </div>
            ) : null}
          </div>

          {/* Error */}
          {error ? (
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-md border border-danger-100 bg-danger-50 px-4 py-3 text-sm text-danger-700" role="alert"><p>{error}</p>{retryKind === "chat" ? <button type="button" disabled={loading} onClick={() => { const lastQuestion = [...messages].reverse().find((item) => item.role === "user")?.content; if (lastQuestion) sendMessage(lastQuestion, true); }} className="font-semibold underline underline-offset-2 disabled:opacity-50">{t("ai.retry", "Retry")}</button> : null}</div>
          ) : null}

          {/* Input */}
          <form
            className="mt-3 flex shrink-0 items-end gap-2 border-t border-surface-border pt-3"
            onSubmit={(event) => {
              event.preventDefault();
              sendMessage();
            }}
          >
            <textarea
              value={input}
              rows={2}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  sendMessage();
                }
              }}
              className="field-shell min-h-[3.25rem] min-w-0 flex-1 resize-none leading-5"
              placeholder={t(
                "ai.placeholder",
                "Ask about crop, irrigation, disease, fertilizer, or market guidance..."
              )}
              maxLength={1200}
              disabled={loading}
              aria-label={t("ai.placeholder", "Ask a question")}
            />

            <button
              type="submit"
              disabled={
                loading || !input.trim()
              }
              aria-label={t("ai.send", "Send")}
              title={t("ai.send", "Send")}
              className="theme-button-primary min-h-[3.25rem] shrink-0 gap-2 px-3 sm:px-4 disabled:opacity-60"
            >
              <Send size={16} aria-hidden="true" />
              <span className="hidden sm:inline">{t("ai.send", "Send")}</span>
            </button>
          </form>

          {/* Disclaimer */}
          <p className="mt-2 text-[11px] leading-4 text-text-subtle sm:text-xs sm:leading-5">
            {t(
              "ai.disclaimer",
              "AI guidance is generated from your project data. Confirm chemical, fertilizer, and local decisions with KVK or an agriculture officer."
            )}
          </p>
        </div>
      </div>
    </section>
  );
}

export default AskAiAssistant;
