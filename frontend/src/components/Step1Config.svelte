<script lang="ts">
  import { getModels, saveConfig } from "../lib/api";

  interface Props {
    onSaved: () => void;
  }

  const { onSaved }: Props = $props();

  let provider = $state("openai");
  let modelsApiKey = $state("");
  let mapsApiKey = $state("");
  let model = $state("");
  let models: string[] = $state([]);
  let modelsLoading = $state(false);
  let modelsError: string | undefined = $state(undefined);
  let saving = $state(false);
  let error: string | undefined = $state(undefined);

  async function loadModels() {
    if (!modelsApiKey) {
      models = [];
      modelsError = undefined;
      return;
    }
    modelsLoading = true;
    modelsError = undefined;
    try {
      const res = await getModels(provider, modelsApiKey);
      models = res.models;
      modelsError = res.error;
      if (res.models.length > 0) model = res.models[0];
    } catch (_) {
      models = [];
      modelsError = "Could not load models — check your API key";
    } finally {
      modelsLoading = false;
    }
  }

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    saving = true;
    error = undefined;
    try {
      await saveConfig({
        provider,
        model,
        api_key: modelsApiKey,
        maps_api_key: mapsApiKey,
      });
      onSaved();
    } catch (err) {
      error =
        err instanceof Error ? err.message : "An unexpected error occurred.";
    } finally {
      saving = false;
    }
  }
</script>

<form onsubmit={handleSubmit}>
  <div class="form-control mb-3">
    <label class="label" for="provider"
      ><span class="label-text">Provider</span></label
    >
    <select
      id="provider"
      class="select select-bordered"
      bind:value={provider}
      onchange={loadModels}
    >
      <option value="openai">OpenAI</option>
      <option value="anthropic">Anthropic</option>
      <option value="google">Google</option>
    </select>
  </div>

  <div class="form-control mb-3">
    <label class="label" for="api-key"
      ><span class="label-text">API Key</span></label
    >
    <input
      id="api-key"
      type="password"
      class="input input-bordered"
      placeholder="Your API key"
      required
      bind:value={modelsApiKey}
      onchange={loadModels}
    />
  </div>

  <div class="form-control mb-4">
    <label class="label" for="model-select">
      <span class="label-text">Model</span>
      {#if modelsLoading}<span class="loading loading-spinner loading-xs"
        ></span>{/if}
    </label>
    <select id="model-select" class="select select-bordered" bind:value={model}>
      {#if models.length === 0}
        <option value="" disabled selected
          >{modelsError ?? "Enter API key to load models..."}</option
        >
      {:else}
        {#each models as m}
          <option value={m}>{m}</option>
        {/each}
      {/if}
    </select>
  </div>

  <div class="form-control mb-4">
    <label class="label" for="maps-api-key">
      <span class="label-text">
        Google Maps API Key <span class="text-base-content/50">(optional)</span>
      </span>
    </label>
    <input
      id="maps-api-key"
      type="password"
      class="input input-bordered"
      bind:value={mapsApiKey}
    />
    <label class="label" for="maps-api-key">
      <span class="label-text-alt text-base-content/50">
        You can set up an API key for free with thousands of calls per month:
        <a
          href="https://developers.google.com/maps/documentation/tile/get-api-key"
          >Click here</a
        >
        <br />
        If you do not provide this key, you can still try to use Guess Explainr, but
        it will become unreliable, as Google might block you from downloading the
        street view panoramas.
      </span>
    </label>
  </div>

  {#if error}
    <p class="text-error text-sm mb-3">{error}</p>
  {/if}

  <button type="submit" class="btn btn-primary w-full" disabled={saving}>
    {saving ? "Saving..." : "Save & Continue"}
  </button>
</form>
