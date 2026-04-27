<script lang="ts">
  import { processUrl } from "../lib/api";
  import type { Country } from "../lib/api";

  interface Props {
    onUrlProcessed: (data: {
      detectedCountry: Country;
      availableCountries: Country[];
      panoramaAvailable: boolean;
    }) => void;
  }

  const { onUrlProcessed }: Props = $props();

  const EXAMPLE_URL =
    "https://www.google.com/maps/@38.0691925,22.2390295,3a,90y,302.4h,92.61t/data=!3m7!1e1!3m5!1sC7dD4mGuuHHm6SjUq80gtw!2e0!6shttps:%2F%2Fstreetviewpixels-pa.googleapis.com%2Fv1%2Fthumbnail%3Fcb_client%3Dmaps_sv.tactile%26w%3D900%26h%3D600%26pitch%3D-2.612560000000002%26panoid%3DC7dD4mGuuHHm6SjUq80gtw%26yaw%3D302.40146!7i16384!8i8192?entry=ttu&g_ep=EgoyMDI2MDEwNC4wIKXMDSoASAFQAw%3D%3D";

  let url = $state("");
  let loading = $state(false);
  let error: string | undefined = $state(undefined);

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    loading = true;
    error = undefined;
    try {
      const res = await processUrl(url);
      onUrlProcessed({
        detectedCountry: res.detected_country,
        availableCountries: res.available_countries,
        panoramaAvailable: res.panorama_available,
      });
    } catch (err) {
      error =
        err instanceof Error ? err.message : "An unexpected error occurred.";
    } finally {
      loading = false;
    }
  }
</script>

<p class="text-base-content/60 text-sm mb-4">
  Copy any Google Maps URL of a location you want to learn about.
</p>

<form onsubmit={handleSubmit}>
  <div class="form-control mb-4">
    <input
      type="url"
      class="input input-bordered w-full"
      placeholder="https://www.google.com/maps/..."
      required
      bind:value={url}
    />
  </div>
  <div class="mb-4">
    <button
      type="button"
      class="btn btn-ghost btn-sm"
      onclick={() => (url = EXAMPLE_URL)}
    >
      Use an example
    </button>
  </div>
  <div class="flex items-center gap-3 flex-wrap">
    <button type="submit" class="btn btn-primary" disabled={loading}
      >Analyze Location</button
    >
    {#if loading}<span class="loading loading-spinner loading-sm"></span>{/if}
    {#if error}<span class="text-error text-sm">{error}</span>{/if}
  </div>
</form>
