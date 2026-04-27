<script lang="ts">
    import {compare} from '../lib/api'
    import type {Country} from '../lib/api'

    interface Props {
        availableCountries: Country[]
        detectedCountry: Country | null
        panoramaAvailable: boolean
        selectedCountries: string[]
        togglecountry: (id: string) => void
        onCompared: (data: { streamUrl: string; context: string }) => void
    }

    const {
        availableCountries,
        detectedCountry,
        panoramaAvailable,
        selectedCountries,
        togglecountry,
        onCompared,
    }: Props = $props()

    let questions = $state('')
    let comparing = $state(false)
    let error: string | undefined = $state(undefined)
    let panoramaOpen = $state(false)

    async function handleSubmit(e: SubmitEvent) {
        e.preventDefault()
        if (selectedCountries.length === 0) return
        comparing = true
        error = undefined
        try {
            const res = await compare(selectedCountries, questions)
            onCompared({streamUrl: res.stream_url, context: res.context})
        } catch (err) {
            error = err instanceof Error ? err.message : 'An unexpected error occurred.'
        } finally {
            comparing = false
        }
    }
</script>

<div>
    <div class="flex items-start gap-4 mb-4">
        {#if panoramaAvailable}
            <div>
                <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
                <img
                        src="/api/panorama-image"
                        onclick={() => (panoramaOpen = true)}
                        class="w-40 h-28 object-cover rounded-lg cursor-pointer hover:opacity-80 transition-opacity flex-shrink-0"
                        alt="Street View panorama"
                />
                {#if panoramaOpen}
                    <dialog open class="modal">
                        <div class="modal-box max-w-5xl p-2">
                            <img src="/api/panorama-image" class="w-full rounded-lg"
                                 alt="Street View panorama (full size)"/>
                        </div>
                        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
                        <div role="dialog" tabindex=0 class="modal-backdrop" onclick={() => (panoramaOpen = false)}>
                            <button>close</button>
                        </div>
                    </dialog>
                {/if}
            </div>
        {/if}

        {#if detectedCountry}
            <div>
      <span class="text-sm font-semibold text-base-content/60 uppercase tracking-wide">
        Detected country
      </span>
                <div class="text-lg mt-1">{detectedCountry.display_name}</div>
            </div>
        {/if}
    </div>

    <div class="mb-4">
        <p class="text-sm text-base-content/60 mb-2">Select countries to compare (max 4):</p>
        <div class="flex flex-wrap gap-2">
            {#each availableCountries as country (country.id)}
                <button
                        type="button"
                        class="rounded-xs badge cursor-pointer"
                        class:badge-primary={selectedCountries.includes(country.id)}
                        class:badge-outline={!selectedCountries.includes(country.id)}
                        class:badge-ghost={!selectedCountries.includes(country.id)}
                        onclick={() => togglecountry(country.id)}
                >{country.display_name}</button>
            {/each}
        </div>
    </div>

    <form onsubmit={handleSubmit}>
        <div class="form-control mb-4">
            <label class="label" for="questions">
                <span class="label-text">Custom questions (optional)</span>
            </label>
            <textarea
                    id="questions"
                    class="textarea textarea-bordered w-full"
                    rows={3}
                    placeholder="for example: How can I separate Sweden from Norway?"
                    bind:value={questions}
            ></textarea>
        </div>
        <div class="flex items-center gap-3 flex-wrap">
            <button
                    type="submit"
                    class="btn btn-primary"
                    disabled={selectedCountries.length === 0 || comparing}
            >
                {comparing ? 'Comparing…' : 'Compare'}
            </button>
            {#if comparing}<span class="loading loading-spinner loading-sm"></span>{/if}
            {#if error}<span class="text-error text-sm">{error}</span>{/if}
        </div>
    </form>
</div>
