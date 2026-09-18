import type { CSSProperties } from 'react'
import megaCharizardX from '../assets/pokemon/mega-charizard-x.png'

const imageStyle: CSSProperties = {
  mixBlendMode: 'screen',
  opacity: 0.6,
  filter: 'grayscale(0.4) saturate(1.5) brightness(0.42) contrast(1.1) drop-shadow(0 0 10px rgba(56,130,190,0.12))',
}

/** Purely decorative background layer for Scan Mode -- not a card, not a
 * panel, no border/background/padding of its own. Renders as a child of a
 * `relative` ancestor with a negative z-index, which places it above that
 * ancestor's own plain background but below every normal-flow sibling (the
 * form, results, etc.) -- that's what makes it read as part of the
 * screen's background instead of a floating sticker. Never interactive: no
 * click target, no scanner meaning, no effect on the form/results. The
 * parent must be `relative overflow-hidden` so this never affects document
 * height or causes horizontal scroll.
 *
 * Two copies flank the form, one mirrored so they face each other instead
 * of both facing the same way. Hidden below `md`: on a narrow phone there
 * isn't enough spare width/height for either copy to read as a subtle
 * background rather than clutter colliding with the form. */
export function CharizardDecor() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 -z-10 hidden select-none overflow-hidden md:block"
    >
      <img src={megaCharizardX} alt="" className="absolute -bottom-6 -right-6 w-[48%] lg:w-[55%]" style={imageStyle} />
      <img
        src={megaCharizardX}
        alt=""
        className="absolute -bottom-6 -left-6 w-[48%] -scale-x-100 lg:w-[55%]"
        style={imageStyle}
      />
    </div>
  )
}
