<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { connectSSE } from "../lib/sse";
  import SvelteMarkdown from "@humanspeak/svelte-markdown";

  interface Props {
    streamUrl: string;
    context: string;
  }

  const { streamUrl, context }: Props = $props();

  interface ChatMessage {
    id: string;
    userText: string;
    responseHtml: string;
    loading: boolean;
  }

  let analysisMarkdown = $state("");
  let analysisError: string | undefined = $state();
  let analysisDone = $state(false);
  let messages: ChatMessage[] = $state([]);
  let chatInput = $state("");
  let chatArea: HTMLDivElement | undefined = $state();

  let cleanupSSE: (() => void) | undefined;

  onMount(() => {
    cleanupSSE = connectSSE(
      streamUrl,
      (data) => {
        analysisMarkdown = data;
      },
      (data) => {
        analysisMarkdown = data;
        analysisDone = true;
      },
      (data) => {
        analysisError = data;
      },
    );
  });

  onDestroy(() => {
    cleanupSSE?.();
  });

  function scrollChat() {
    setTimeout(() => {
      if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
    }, 50);
  }

  function sendChat(e: SubmitEvent) {
    e.preventDefault();
    const msg = chatInput.trim();
    if (!msg) return;
    chatInput = "";

    const id = crypto.randomUUID();
    messages = [
      ...messages,
      { id, userText: msg, responseHtml: "", loading: true },
    ];
    scrollChat();

    const url = `/api/chat?message=${encodeURIComponent(msg)}&context=${encodeURIComponent(context)}`;
    const es = new EventSource(url);

    es.addEventListener("done", (e: MessageEvent) => {
      messages = messages.map((m) =>
        m.id === id ? { ...m, responseHtml: e.data, loading: false } : m,
      );
      es.close();
      scrollChat();
    });

    es.onerror = () => {
      messages = messages.map((m) =>
        m.id === id
          ? {
              ...m,
              responseHtml: '<p class="text-error">Error loading response</p>',
              loading: false,
            }
          : m,
      );
      es.close();
    };
  }
</script>

<div class="prose max-w-none mb-6">
  {#if !analysisDone}
    <div class="flex items-center gap-2 text-sm text-base-content/60">
      <span class="loading loading-dots loading-xs"></span>
      <span>Analyzing...</span>
    </div>
  {/if}

  <!-- TODO: use streaming feature -->
  <SvelteMarkdown source={analysisMarkdown} />

  {#if analysisError !== undefined}
    <p class="text-error">
      {analysisError}
    </p>
  {/if}
</div>

<div class="divider"></div>

<div
  bind:this={chatArea}
  class="flex flex-col gap-3 mb-4 max-h-[36rem] overflow-y-auto scroll-smooth"
>
  {#each messages as msg (msg.id)}
    <div class="chat chat-end">
      <div class="chat-bubble chat-bubble-primary">{msg.userText}</div>
    </div>
    <div class="chat chat-start">
      <div class="chat-bubble prose max-w-none">
        {#if msg.loading}
          <span class="loading loading-dots loading-sm"></span>
        {:else}
          {@html msg.responseHtml}
        {/if}
      </div>
    </div>
  {/each}
</div>

<form onsubmit={sendChat} class="flex gap-2">
  <input
    name="message"
    type="text"
    class="input input-bordered flex-1"
    placeholder="Ask a follow-up question…"
    autocomplete="off"
    bind:value={chatInput}
  />
  <button type="submit" class="btn btn-primary">Send</button>
</form>

<div class="mt-12 text-xs">
  All textual content (i.e., not program code or images) is published under
  <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/"
    >CC BY-NC-SA 4.0</a
  >. The original content is attributed to www.plonkit.com.
</div>
