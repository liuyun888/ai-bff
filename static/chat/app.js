/*!
 * 课次 10.05 · 浏览器消费 BFF SSE
 * 要点：fetch + ReadableStream；自建 buffer 防半包；AbortController 停止。
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
   * 与 Python app/sse_parse.py 心智一致，方便对照。
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
          // 流结束仍有残留：尝试再拆一次（通常 done 已完整）
          this.push("\n\n");
        }
      },
    };
  }

  /**
   * 前端主路径：POST + Authorization + 逐 token 回调。
   */
  async function streamChat(message, modelId, token, onToken, onDone, onError, signal) {
    const res = await fetch("/api/chat/stream", {
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
    if (!res.body) throw new Error("浏览器未提供 ReadableStream");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    const parser = createSseParser(function (evt) {
      if (evt.type === "token" && typeof evt.text === "string") onToken(evt.text);
      else if (evt.type === "error") onError(new Error(evt.message || "stream error"));
      else if (evt.type === "done") onDone(evt);
    });

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      parser.push(decoder.decode(value, { stream: true }));
    }
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
          setStatus("done", "done");
          elMeta.textContent = JSON.stringify(
            {
              tenant_id: doneEvt.tenant_id,
              user_id: doneEvt.user_id,
              model_id: doneEvt.model_id,
              request_id: doneEvt.request_id,
            },
            null,
            0
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

  setStatus("idle · 同源访问本页，Authorization 走 fetch 头", "idle");
})();
