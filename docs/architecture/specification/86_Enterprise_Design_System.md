# 86 — Enterprise Design System

## Purpose

This document defines the Cerebrum Design System: the visual language, design tokens, color system, and typography that every page and component draws from exclusively, per [85_Frontend_Architecture.md](85_Frontend_Architecture.md)'s Design-System-First mandate.

## Scope

This document covers visual language and design tokens. It does not cover the component catalog built from these tokens (see [87_Component_Library.md](87_Component_Library.md)). It specifies token *categories* and named choices, not literal implementation values (hex codes, exact pixel values) — those are Deferred to Architecture-time design-token implementation, consistent with this specification's documentation-only scope.

## Definitions

- **Design Token** — A named, centrally defined value (a color, a spacing unit, a shadow) that components reference rather than hardcoding, ensuring visual consistency and making a system-wide visual change a token update, not a per-component edit.
- **Glassmorphism** — A visual style using translucent, blurred, layered surfaces to create depth without heavy shadows or skeuomorphic texture.

## Visual Language

The Cerebrum visual identity is:

| Characteristic | Description |
|---|---|
| Dark Theme First | The primary, default experience is dark; a light theme is a secondary, fully-supported alternative (per [87_Component_Library.md](87_Component_Library.md)'s required Dark/Light states), not an afterthought. |
| Premium Glassmorphism | Translucent, layered surfaces used deliberately for elevation and depth, not decoratively. |
| Soft gradients | Subtle, low-contrast gradients for surface texture and accent emphasis. |
| Layered translucent surfaces | Depth is communicated through layering and blur, not drop shadows alone. |
| Rounded corners | 12–20px radius range, applied consistently per the Border Radius token scale below. |
| Subtle borders | Low-contrast borders delineating surfaces without harsh separation. |
| Low-noise interface | Minimal decorative elements; every visual element earns its place. |
| High whitespace | Generous spacing supporting the "Extremely fast" and "Zero visual clutter" philosophy goals from [85_Frontend_Architecture.md](85_Frontend_Architecture.md). |
| Smooth animations | Consistent with [85_Frontend_Architecture.md](85_Frontend_Architecture.md)'s Microinteractions, using the Motion token below. |
| Rich typography | Clear hierarchy and readable type, per the Typography section below. |
| Enterprise professionalism | The governing constraint on every other characteristic — premium, not gimmicky. |

**Explicitly avoided:** Neon overload, Excessive shadows, Overly bright colors, Clutter, Skeuomorphism. These are stated as binding exclusions, not merely stylistic suggestions — a proposed component or page exhibiting any of these is non-compliant with the Design System regardless of how it otherwise scores against the Visual Language table above.

## Design Tokens

The following eleven token categories SHALL be centralized in the Design System, referenced by every component, with **no hardcoded values** permitted anywhere in the Frontend Layer outside the token definitions themselves:

Color tokens, Typography tokens, Spacing scale (8-point grid), Border radius, Shadows, Blur, Opacity, Motion, Elevation, Z-index, Icon sizes.

| Token Category | Governing Rule |
|---|---|
| Spacing scale | An 8-point grid — every spacing value is a multiple of 8px (with a documented exception process for the rare sub-grid adjustment, Deferred to Architecture). |
| Border radius | 12–20px range per the Visual Language table, expressed as a small, named scale (e.g., `radius-sm`/`radius-md`/`radius-lg`) rather than arbitrary per-component values. |
| Elevation / Z-index | A single, centrally defined stacking order — no component defines its own z-index value outside this scale, preventing the class of bug where two independently developed components fight over stacking order. |
| Motion | Duration and easing curves, bounded by [85_Frontend_Architecture.md](85_Frontend_Architecture.md)'s <250ms Microinteractions rule and the Reduced Motion accessibility requirement. |

**Binding rule:** No hardcoded values. A component specifying a raw color, pixel value, or duration outside the token system is non-compliant with the Design-System-First mandate ([85_Frontend_Architecture.md](85_Frontend_Architecture.md)), equivalent in severity to a domain bypassing its repository port in the backend architecture.

## Color System

| Role | Named Choice |
|---|---|
| Primary Accent | Electric Blue |
| Secondary Accent | Purple |
| Success | Emerald |
| Warning | Amber |
| Danger | Red |
| Information | Cyan |
| Background | Near-black layered surfaces (Dark Theme First) |

**Binding rule:** Use semantic color tokens only. A component references `color-danger`, never a raw color value — this is what allows the entire Danger semantic (currently Red) to be re-themed platform-wide via a single token change, and is what makes the Design System, not any individual component, the source of truth for what "danger" looks like. This directly mirrors the Explicit over Implicit and Single Source of Truth principles from [04_Project_Principles.md](04_Project_Principles.md), applied to visual design.

## Typography

| Element | Choice |
|---|---|
| Font (primary) | Inter |
| Font (monospace) | JetBrains Mono — used for Code Viewer, technical identifiers, and any content where character-width consistency matters. |

**Hierarchy:** Display, H1, H2, H3, Body, Caption, Code — a fixed seven-level scale every page's text content maps onto, with no ad hoc font-size deviation outside this hierarchy.

**Governing rules:** Readable line lengths (bounded measure, avoiding both cramped and overly wide text blocks) and consistent spacing (line-height and paragraph spacing drawn from the Spacing scale token, not set per-instance).

## Responsibilities

- Any new visual treatment proposed in a later phase must be expressed as a Design Token addition or a new Component Library entry ([87_Component_Library.md](87_Component_Library.md)), never as an inline, one-off style.
- The "explicitly avoided" list (Neon overload, Excessive shadows, etc.) must be treated as a design-review checklist item, not merely descriptive prose.

## Constraints

- This document does not specify exact hex values, pixel measurements, or duration values — these are Deferred to Architecture-time design-token implementation, consistent with the "do not implement" scope of this CES phase.
- Light theme is a required, fully-supported alternative, not a lower-priority afterthought, despite Dark Theme First's status as the default.

## Future Considerations

- As the platform is used across more device classes and contexts, additional semantic color tokens (e.g., a distinct "AI-generated content" accent, tying into [44_Global_Entity_Model.md](44_Global_Entity_Model.md)'s Content Provenance Envelope) may be warranted to visually distinguish AI-generated from human-authored content directly in the UI — a plausible, valuable extension not yet specified here.

## Acceptance Criteria

- [ ] All eleven Visual Language characteristics and the five explicitly avoided treatments from the governing specification are defined.
- [ ] All eleven Design Token categories from the governing specification are defined, with the no-hardcoded-values rule stated as binding.
- [ ] The seven-item Color System and its semantic-tokens-only rule are defined.
- [ ] Typography's font choices, seven-level hierarchy, and governing rules are defined.
