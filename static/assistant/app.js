/*!
 * 课次 11.05 · 统一助手聊天页（与 10.05 /static/chat 分立，勿互相覆盖）
 * 入口：/assistant → POST /api/assistant/stream
 */
(function () {
  "use strict";

  /** @type {AbortController | null} */
  let controller = null;

  const elToken = document.getElementById("token");
  const elModel = document.getElementById("modelId");
  const elMsg = document.getElementById("message");
  const elReply = document.getElementById("reply");
  const elStatus = document.getElementById("status");
  const elMeta = document.getElementById("meta");
  const btnSend = document.getElementById("btnSend");
  const btnStop = document.getElementById("btnStop");

  function setStatus(text, kind) {
    elStatus.textContent = text;
    elStatus.dataset.kind = kind || "idle";
  }

  /**
   * 把字节流按 SSE 事件边界（空行）拆开；半包留在 buffer。
   * 与 10.05 app.js / Python sse_parse 心智一致。
   */
  function createSseParser(onEvent) {
    let buf = "";
    return {
      push(chunkText) {
        buf += chunkText;
        const parts = buf.split("\n\n");
        buf = parts.pop() || "";
        for (const part of parts) {
          const line = part.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          const raw = line.slice(5).trim();
          if (!raw) continue;
          let evt;
          try {
            evt = JSON.parse(raw);
          } catch (e) {
            onEvent({ type: "error", message: "JSON 半包或损坏: " + raw });
            continue;
          }
          onEvent(evt);
        }
      },
      flush() {
        if (buf.trim()) {
          this.push("\n\n");
        }
      },
    };
  }

  /** POST 统一助手流。 */
  async function streamChat(message, modelId, token, onToken, onDone, onError, signal) {
    const res = await fetch("/api/assistant/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + token,
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ message: message, modelId: modelId || "default" }),
      signal: signal,
    });

    if (!res.ok) {
      let detail = "HTTP " + res.status;
      try {
        const j = await res.json();
        if (j && j.detail) detail += " · " + JSON.stringify(j.detail);
      } catch (_) {}
      throw new Error(detail);
    }

    if (!res.body) {
      throw new Error("响应无 body（无法流式读取）");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    const parser = createSseParser(function (evt) {
      if (!evt || !evt.type) return;
      if (evt.type === "token" && typeof evt.text === "string") {
        onToken(evt.text);
      } else if (evt.type === "done") {
        onDone(evt);
      } else if (evt.type === "error") {
        onError(new Error(evt.message || "stream error"));
      }
    });

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      parser.push(decoder.decode(value, { stream: true }));
    }
    parser.push(decoder.decode());
    parser.flush();
  }

  function setStreaming(on) {
    btnSend.disabled = on;
    btnStop.disabled = !on;
    elMsg.disabled = on;
  }

  async function onSend() {
    const token = (elToken.value || "").trim();
    const message = (elMsg.value || "").trim();
    if (!token) {
      setStatus("请填写 Bearer Token（如 tok-alice）", "error");
      return;
    }
    if (!message) {
      setStatus("请输入消息", "error");
      return;
    }

    controller = new AbortController();
    elReply.textContent = "";
    elMeta.textContent = "";
    setStreaming(true);
    setStatus("streaming…", "streaming");

    try {
      await streamChat(
        message,
        elModel.value,
        token,
        function (t) {
          elReply.textContent += t;
        },
        function (doneEvt) {
          setStatus("done · mode=" + (doneEvt.mode || "?"), "done");
          elMeta.textContent = JSON.stringify(
            {
              mode: doneEvt.mode,
              action: doneEvt.action,
              guard_triggered: doneEvt.guard_triggered,
              case_id: doneEvt.case_id,
              tenant_id: doneEvt.tenant_id,
              user_id: doneEvt.user_id,
              model_id: doneEvt.model_id,
              request_id: doneEvt.request_id,
              session_id: doneEvt.session_id,
              elapsed_ms: doneEvt.elapsed_ms,
            },
            null,
            2
          );
        },
        function (err) {
          throw err;
        },
        controller.signal
      );
      if (elStatus.textContent === "streaming…") setStatus("done", "done");
    } catch (err) {
      if (err && err.name === "AbortError") {
        setStatus("aborted（已停止）", "aborted");
      } else {
        setStatus(String(err && err.message ? err.message : err), "error");
      }
    } finally {
      setStreaming(false);
      controller = null;
    }
  }

  function onStop() {
    if (controller) controller.abort();
  }

  btnSend.addEventListener("click", onSend);
  btnStop.addEventListener("click", onStop);
  elMsg.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!btnSend.disabled) onSend();
    }
  });

  setStatus("idle · /assistant → /api/assistant/stream", "idle");
})();
