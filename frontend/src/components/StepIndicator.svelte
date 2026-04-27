<script lang="ts">
    interface Props {
        step: number
        maxReached: number
        onStepClick: (n: number) => void
    }

    const {step, maxReached, onStepClick}: Props = $props()

    const steps = [
        {label: 'LLM Config', n: 1},
        {label: 'Maps URL', n: 2},
        {label: 'Compare', n: 3},
        {label: 'Analysis', n: 4},
    ]
</script>

<ul class="steps w-full mb-8">
    {#each steps as s}
        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
        <li
                class="step"
                class:step-primary={step >= s.n}
                class:cursor-pointer={maxReached >= s.n}
                onclick={() => onStepClick(s.n)}
        >{s.label}</li>
    {/each}
</ul>
