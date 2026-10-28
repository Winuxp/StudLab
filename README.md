# StudLab 1.2 — physical bottom-up decomposition

Standalone Python/Streamlit engineering prototype, independent of Tolerator. Replace the **whole studlab folder** when updating: this release changes both the geometry schema and the editor. Restart the app.

## Start on macOS

Open a terminal in the extracted `studlab` folder:

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

On Windows use `py` or `python` instead of `python3`. No Node, build step, CDN or extra browser plugin is required. The editor's HTML/JavaScript is bundled locally in `editor/index.html`. Keep that folder next to `app.py`. For Streamlit Cloud, upload the whole project including this folder and select `studlab/app.py` (or `app.py` at repository root).

## Physical lengths and origin

Coordinates are measured **bottom → top**. At z = 0, the lower male thread and the female anchor thread start together. Their physical lengths are independent. The first interval ends at whichever of these ends first; the next interval continues the remaining geometry. All remaining stud, joint, washer and nut boundaries are merged in the same way. The C1, C2… column and interval table show this intersection decomposition.

The two end threads are permanent physical elements: S1 is the lower thread, initially S3 the upper thread. Body segments can be inserted between them, with stable IDs (e.g. S4 can appear below S3). P1, P2… are clamped parts ordered bottom → top. IDs are stable, not a renumbering of physical position. Add/remove body segments or clamped parts with the editor's buttons; at least one body and one clamped part remain.

The anchor's female physical length defines the start of the clamped stack. The washer is above the last clamped part and the nut above the washer. The upper male thread has independent start/end coordinates derived from the preceding stud lengths. Upper male and nut threads can therefore start or finish at different coordinates.

Male thread longer than female: the free excess within the load path is included. Female thread longer than male: unused female thread can surround a reduced plain body if the entered body diameter clears the female root reference. Such a body section is still loaded and included, even though it lies inside an unused tapped portion. Interference with a full-diameter plain body is flagged. These reference root-clearance checks do not replace real thread/fit tolerances or a lead-in/runout model.

A stud protruding above the nut is allowed. A nut extending beyond the stud is a warning, rather than automatically an error, provided actual engagement remains positive and accommodates the entered equivalent lengths. This is **not** a thread-stripping or minimum engagement safety verification.

## Geometric decomposition is not elastic decomposition

Physical lower engagement = overlap of [0, lower male end] and [0, female anchor end]. Upper engagement = overlap of the upper external thread and the nut's internal-thread interval.

The start of the freely loaded male path is the **end of lower engagement**, not necessarily the anchor face. Its upper end is the **start of upper engagement**, not necessarily the nut bearing face. Unengaged loaded sections inside unused female threads must not be omitted.

Each free cylindrical/threaded length is counted once in the elastic chain. The geometric C intervals may additionally split at part/washer boundaries for display; they are not added as extra springs. Portions outside the active path are geometric/unloaded and not counted as full-force tensile springs.

## Engaged regions and reference inputs

Do **not** count the complete physical length of an engaged thread as a cylinder uniformly carrying the preload. The engine separates free stud regions and equivalent male/female end springs.

For each end, enter:

- Physical male/female lengths (drawing geometry).
- Male axial equivalent factor `kg`: `LG = kg × d`; `CG = LG / (Estud × A3)`.
- Female axial equivalent factor `km`: `LM = km × d`; `CM = LM / (Efemale × AN)`.
- Independent torsion equivalent length `Ltors` in mm.

`A3 = π d3²/4`, `AN = π d²/4`. Initial axial reference inputs are **kg = 0.5** at both ends, **km = 0.4** for the nut and **km = 0.33** for the tapped anchor. These reference substitutions are associated with the VDI 2230 engaged-region approach; their applicability, material choice and connection-type assumptions for the actual stud must be verified against your licensed edition. They are editable model inputs, not an automated compliance determination. The app rejects a male axial equivalent length exceeding the actual engaged overlap; it does not extrapolate to physically insufficient engagement.

Axial substitution factors are **not automatically reused in torsion**. Each end's Ltors defaults to **0 mm**, meaning engaged-region twist is omitted. If a justified torsional equivalent is available, enter it separately. The free path's torsion is always included. The displayed angle is therefore conditional on these torsion inputs and does not claim the full VDI torsional treatment.

Female springs represent local thread/nut/anchor load-transfer movement; they are added separately to the axial compatibility sum. They do not also appear as clamped-part annuli, preventing double counting. Engaged-region nominal stress is reported using full target tension and thread torque as a section check; actual thread-load distribution, root concentration and stripping resistance are not solved.

## Focus highlighting, errors and length suggestions

The geometry editor and diagram are in the **same local browser component**. Focusing a field with the mouse or keyboard highlights its element and related C intervals **immediately**, without waiting for Enter, blur or a server round trip. It does not infer focus from the last saved change. Red geometry-error outlines take precedence over orange focus outlines.

A changed value is committed when Enter is pressed or the field is left; calculation and physical drawing are then refreshed by Python. Focus is restored after that refresh where possible. Uncommitted keystrokes do not launch a new calculation.

During a length/engagement/interference error, focusing a field on an element displays an available proposed **length** beside the diagram. **Use this length** applies it explicitly. The proposal usually aligns the male tip with the nut top, or moves the upper thread start to the nut face when that is the conflict. It preserves all other entered dimensions. Protrusion may be intentional, so the proposal is not applied automatically.

A proposal corrects a stated axial relationship, **not all possible geometry problems**. Other clearances, engagement substitutions and strength/pressure limits are rechecked after applying it; no automatic guarantee of complete consistency is made. Only positive proposed lengths are offered.

## Calculation engine

Inputs use mm, N, GPa (converted to MPa), and dimensionless coefficients. Internal torque is N·mm. Single-start, right-hand 60° metric reference threads are selected independently for the upper nut and lower anchor.

Thread database `threads.json`: 25 seed coarse/fine entries M3–M30, not a complete tolerance database. Derived reference geometry:

`d2 = d − 0.6495190528 P`

`d3 = d − 1.226869322 P`

`As = π/4 × [(d2+d3)/2]²`.

Optional per-entry `d2_mm`, `d3_mm`, `As_mm2` override these references. Use drawing/standard/manufacturing data for the actual thread.

Free plain region: `C = L/(E A)`, `A = π d²/4`. Free threaded region: elastic area `A3`; nominal tensile stress area `As`. Annular clamped region: `A = π(Deff² − Dh²)/4`; the washer is one additional annulus. Deff must represent participating compression area, not automatically the entire part OD. Pressure cones and local washer bending are not implemented.

For the **upper** thread: `φ = atan[P/(π d2)]`, `ρ′ = atan[μG/cos30°]`.

`MG = F d2/2 tan(φ+ρ′)`.

`MK = F μK DKm/2`, with uniform-pressure mean bearing diameter `DKm = (2/3)(Do³−Di³)/(Do²−Di²)`.

`MA = MG + MK`. Only MG, not MA, drives stud torsion. The lower thread is anchored; it does not act as a second tightening helix. The washer is stationary and the clamped stack reacts MK; stack torsion is omitted.

Snug preload: `F0 = 1000 Msnug / (MA/F)` for constant friction. F0 above target is rejected. This assumes interfaces are already seated at snug; running torque and prevailing thread torque are omitted.

Total axial compatibility `Ctotal = Cfree + CG_lower + CG_upper + CM_lower + CM_upper + Cparts + Cwasher`.

`θhelix = 360/P × [(F−F0) Ctotal + additional closure]`.

`G = E/[2(1+ν)]`, `J = π d⁴/32`; threaded torsion uses d3. Total torsional compliance is the sum of free-path `L/(GJ)` and the entered end torsion equivalents.

`Δθtwist = [MG(F)−MG(F0)] Ct × 180/π`.

**`θtool = θhelix + Δθtwist`**.

Target tension is at the end of tightening before tool release, residual torsional relaxation and later settlement. Extra seating closure is an entered irreversible movement during the angle step, not post-assembly embedding loss.

Nominal section stresses: `σ = F/As` (threaded) or F/A (plain); `τ = MG d/(2J)`; `σvM = sqrt(σ²+3τ²)`. No notch/fatigue factor. Rp0.2 is entered per stud element. If an elastic or entered pressure limit is exceeded, the primary angle/torque instruction is unavailable; detailed values are labelled elastic extrapolations.

Pressure checks: clamped-part average compression, nut/washer bearing annulus, washer bulk and washer/top-part overlap. These are average annular pressures, not local contact-FEA predictions.

## Scope and validation

This is a **VDI-oriented prototype**, not a complete VDI 2230 calculation or compliance report. Missing verification includes normative compression bodies/load introduction, connection-type validation of all substitutions, engagement/stripping strength, thread tolerances and chamfers/runouts, service forces, bending/eccentricity, fatigue, thermal changes, tightening scatter, plasticity, tool/stack compliance and post-release effects. Reference values and model assumptions must be checked against the actual assembly and licensed guideline.

Tests include boundary intersections in both male/female length orders, reduced shank inside unused female thread, equivalent versus physical lengths, splitting invariance (no duplicate springs), independent torsion lengths, correction proposals, errors, legacy engine checks and Streamlit execution. The local editor's focus/commit/add/remove/suggestion handlers are checked in a DOM environment; a full Safari/Chrome integration test was not available in this workspace. Please report any browser-specific focus or sizing issue.

Primary references:

- [VDI 2230 Part 1 — publisher scope](https://www.vdi.de/en/home/vdi-standards/details/vdi-2230-blatt-1-systematic-calculation-of-highly-stressed-bolted-joints-joints-with-one-cylindrical-bolt).
- [Schaeffler technical pocket guide — fixing screws, printed p. 511](https://www.schaeffler.com/remotemedien/media/_shared_media/08_media_library/01_publications/schaeffler_2/catalogue_1/downloads_6/stt_de_en.pdf): torque decomposition and reference thread area.
- [PCB Load & Torque — review of VDI 2230](https://www.pcb.com/Contentstore/mktgcontent/WhitePapers/WPL_22_Guideliner_VDI_2230.pdf): engaged versus unengaged behaviour and need for engagement-strength checks. Not a source of an automatically certified stud model.

Run Python checks from the project folder: `python3 -m unittest discover -q`. JSON export contains the complete physical model and results; CSV contains free/engaged/part detail rows. JSON import is not implemented.
