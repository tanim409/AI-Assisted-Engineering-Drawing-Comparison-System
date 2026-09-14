import React from 'react';

interface CADVectorRendererProps {
  drawingType: string;
  revision: 'A' | 'B';
  invertColors?: boolean;
  highlightCategory?: string | null;
  activeChangeId?: string | null;
}

export const CADVectorRenderer: React.FC<CADVectorRendererProps> = ({
  drawingType,
  revision,
  invertColors = false,
  activeChangeId,
}) => {
  const isDark = invertColors;
  const strokeColor = isDark ? '#E5E5E5' : '#171717';
  const mutedColor = isDark ? '#737373' : '#737373';
  const gridColor = isDark ? '#262626' : '#E5E5E5';
  const centerLineColor = isDark ? '#60A5FA' : '#2563EB';
  const dimensionColor = isDark ? '#F59E0B' : '#B45309';
  const bgColor = isDark ? '#0D0D0D' : '#FAFAFA';

  if (drawingType === 'ARCH_REV_A' || drawingType === 'ARCH_REV_B' || drawingType === 'arch-level-4-core') {
    return (
      <svg
        viewBox="0 0 1000 700"
        className="w-full h-full select-none"
        style={{ backgroundColor: bgColor }}
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="arch-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke={gridColor} strokeWidth="0.5" strokeDasharray="2,2" />
          </pattern>
          <pattern id="hatch-concrete" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="10" stroke={mutedColor} strokeWidth="0.8" opacity="0.4" />
          </pattern>
        </defs>

        <rect width="1000" height="700" fill="url(#arch-grid)" />

        {/* Outer Boundary Walls */}
        <rect x="80" y="80" width="840" height="520" fill="none" stroke={strokeColor} strokeWidth="4" />
        <rect x="90" y="90" width="820" height="500" fill="none" stroke={strokeColor} strokeWidth="1.5" />

        {/* Core Elevator & Stair Shaft */}
        <rect x="220" y="180" width="220" height="260" fill="url(#hatch-concrete)" stroke={strokeColor} strokeWidth="3" />
        <line x1="220" y1="180" x2="440" y2="440" stroke={strokeColor} strokeWidth="1" strokeDasharray="4,4" />
        <line x1="440" y1="180" x2="220" y2="440" stroke={strokeColor} strokeWidth="1" strokeDasharray="4,4" />
        <text x="330" y="315" fill={mutedColor} fontSize="14" fontFamily="monospace" textAnchor="middle">
          LIFT SHAFT 01 & 02
        </text>

        {/* HVAC Riser Shaft (CHG-02) */}
        {revision === 'A' ? (
          <g>
            <rect x="240" y="370" width="80" height="55" fill="none" stroke={strokeColor} strokeWidth="2.5" />
            <line x1="240" y1="370" x2="320" y2="425" stroke={strokeColor} strokeWidth="1" />
            <line x1="320" y1="370" x2="240" y2="425" stroke={strokeColor} strokeWidth="1" />
            <text x="280" y="445" fill={dimensionColor} fontSize="11" fontFamily="monospace" textAnchor="middle">
              RISER 600×400
            </text>
          </g>
        ) : (
          <g>
            <rect x="235" y="360" width="110" height="75" fill="none" stroke="#D97706" strokeWidth="2.5" />
            <line x1="235" y1="360" x2="345" y2="435" stroke="#D97706" strokeWidth="1" />
            <line x1="345" y1="360" x2="235" y2="435" stroke="#D97706" strokeWidth="1" />
            <text x="290" y="455" fill="#D97706" fontSize="11" fontWeight="bold" fontFamily="monospace" textAnchor="middle">
              RISER 800×550 [REVISED]
            </text>
          </g>
        )}

        {/* Corridor Egress & Doors (CHG-01) */}
        <line x1="480" y1="80" x2="480" y2="280" stroke={strokeColor} strokeWidth="3" />
        <line x1="560" y1="80" x2="560" y2="280" stroke={strokeColor} strokeWidth="3" />

        {revision === 'A' ? (
          <g>
            {/* Open archway */}
            <line x1="480" y1="200" x2="560" y2="200" stroke={mutedColor} strokeWidth="1" strokeDasharray="3,3" />
            <text x="520" y="190" fill={mutedColor} fontSize="11" fontFamily="monospace" textAnchor="middle">
              OPEN EGRESS (1800mm)
            </text>
          </g>
        ) : (
          <g>
            {/* FD120 Double Door Addition */}
            <line x1="480" y1="200" x2="560" y2="200" stroke="#059669" strokeWidth="2.5" />
            <path d="M 480 200 A 35 35 0 0 1 515 165" fill="none" stroke="#059669" strokeWidth="1.5" strokeDasharray="3,2" />
            <line x1="480" y1="200" x2="515" y2="165" stroke="#059669" strokeWidth="2" />
            <path d="M 560 200 A 35 35 0 0 0 525 165" fill="none" stroke="#059669" strokeWidth="1.5" strokeDasharray="3,2" />
            <line x1="560" y1="200" x2="525" y2="165" stroke="#059669" strokeWidth="2" />
            <text x="520" y="150" fill="#059669" fontSize="11" fontWeight="bold" fontFamily="monospace" textAnchor="middle">
              FD120 DOUBLE DOOR [NEW]
            </text>
          </g>
        )}

        {/* East Wall & Hose Reel (CHG-03) */}
        <line x1="680" y1="80" x2="680" y2="600" stroke={strokeColor} strokeWidth="3" />
        {revision === 'A' ? (
          <g>
            <rect x="670" y="320" width="30" height="60" fill="none" stroke="#E11D48" strokeWidth="2" />
            <circle cx="685" cy="350" r="14" fill="none" stroke="#E11D48" strokeWidth="1.5" />
            <text x="735" y="355" fill="#E11D48" fontSize="10" fontFamily="monospace">
              FIRE HOSE REEL
            </text>
          </g>
        ) : (
          <g>
            <line x1="680" y1="320" x2="680" y2="380" stroke={strokeColor} strokeWidth="3" />
            <text x="710" y="355" fill={mutedColor} fontSize="10" fontFamily="monospace">
              [FLUSH DRYWALL]
            </text>
          </g>
        )}

        {/* Demising Wall & Notes (CHG-04) */}
        <line x1="80" y1="460" x2="680" y2="460" stroke={strokeColor} strokeWidth="3" />
        <rect x="110" y="490" width="260" height="80" fill="none" stroke={gridColor} strokeWidth="1" />
        <text x="120" y="515" fill={strokeColor} fontSize="12" fontWeight="bold" fontFamily="monospace">
          {revision === 'A' ? 'SPEC: WALL TYPE W-2 (STC 45)' : 'SPEC: WALL TYPE W-4A (STC 55) [REV 04]'}
        </text>
        <text x="120" y="535" fill={mutedColor} fontSize="10" fontFamily="monospace">
          {revision === 'A' ? 'Standard 13mm Plasterboard on 70mm studs' : 'Double 16mm SoundBloc + Resilient Channel'}
        </text>

        {/* Title Block */}
        <g transform="translate(680, 500)">
          <rect x="0" y="0" width="240" height="100" fill={bgColor} stroke={strokeColor} strokeWidth="1.5" />
          <line x1="0" y1="30" x2="240" y2="30" stroke={strokeColor} strokeWidth="1" />
          <line x1="0" y1="65" x2="240" y2="65" stroke={strokeColor} strokeWidth="1" />
          <text x="12" y="20" fill={strokeColor} fontSize="11" fontWeight="bold" fontFamily="monospace">
            ARC-L4-FP-401 | LEVEL 4 CORE
          </text>
          <text x="12" y="50" fill={mutedColor} fontSize="10" fontFamily="monospace">
            STATUS: {revision === 'A' ? 'APPROVED BASELINE' : 'REVISED SUBMISSION'}
          </text>
          <text x="12" y="85" fill={revision === 'B' ? '#D97706' : strokeColor} fontSize="12" fontWeight="bold" fontFamily="monospace">
            REVISION: {revision === 'A' ? 'REV 03' : 'REV 04'}
          </text>
        </g>
      </svg>
    );
  }

  if (drawingType === 'PCB_REV_A' || drawingType === 'PCB_REV_B' || drawingType === 'elec-pcb-mcu') {
    return (
      <svg
        viewBox="0 0 1000 700"
        className="w-full h-full select-none"
        style={{ backgroundColor: bgColor }}
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="pcb-grid" width="25" height="25" patternUnits="userSpaceOnUse">
            <circle cx="12.5" cy="12.5" r="0.75" fill={gridColor} />
          </pattern>
        </defs>
        <rect width="1000" height="700" fill="url(#pcb-grid)" />

        {/* MCU Package U1 */}
        <rect x="360" y="220" width="280" height="260" fill="none" stroke={strokeColor} strokeWidth="2.5" rx="4" />
        <circle cx="380" cy="240" r="4" fill={strokeColor} />
        <text x="500" y="340" fill={strokeColor} fontSize="16" fontWeight="bold" fontFamily="monospace" textAnchor="middle">
          STM32H743IIT6
        </text>
        <text x="500" y="365" fill={mutedColor} fontSize="11" fontFamily="monospace" textAnchor="middle">
          LQFP-176 / 480 MHz MCU
        </text>

        {/* I2C Pullups (CHG-01) */}
        <path d="M 220 280 L 360 280" fill="none" stroke={strokeColor} strokeWidth="1.5" />
        <path d="M 280 280 L 280 220" fill="none" stroke={strokeColor} strokeWidth="1.5" />
        <rect x="268" y="170" width="24" height="40" fill={bgColor} stroke={revision === 'B' ? '#D97706' : strokeColor} strokeWidth="1.5" />
        <text x="300" y="195" fill={revision === 'B' ? '#D97706' : strokeColor} fontSize="11" fontWeight="bold" fontFamily="monospace">
          R18: {revision === 'A' ? '4.7kΩ' : '2.2kΩ (REV 1.4)'}
        </text>
        <line x1="280" y1="170" x2="280" y2="140" stroke={strokeColor} strokeWidth="1.5" />
        <text x="280" y="130" fill={strokeColor} fontSize="11" fontFamily="monospace" textAnchor="middle">
          +3.3V
        </text>

        {/* Ferrite Bead Filter (CHG-02) */}
        <path d="M 640 280 L 780 280" fill="none" stroke={strokeColor} strokeWidth="1.5" />
        {revision === 'A' ? (
          <g>
            <text x="710" y="270" fill={mutedColor} fontSize="10" fontFamily="monospace">
              VDDA DIRECT LINK
            </text>
          </g>
        ) : (
          <g>
            <rect x="690" y="265" width="40" height="30" fill={bgColor} stroke="#059669" strokeWidth="2" />
            <text x="710" y="285" fill="#059669" fontSize="10" fontWeight="bold" fontFamily="monospace" textAnchor="middle">
              FB3
            </text>
            <text x="710" y="320" fill="#059669" fontSize="10" fontFamily="monospace" textAnchor="middle">
              BLM18 120Ω
            </text>
          </g>
        )}

        {/* BOOT Header J3 (CHG-03) */}
        {revision === 'A' ? (
          <g>
            <rect x="680" y="420" width="35" height="50" fill={bgColor} stroke="#E11D48" strokeWidth="1.5" />
            <circle cx="697" cy="435" r="3" fill="#E11D48" />
            <circle cx="697" cy="455" r="3" fill="#E11D48" />
            <text x="725" y="445" fill="#E11D48" fontSize="10" fontFamily="monospace">
              J3 (BOOT0)
            </text>
          </g>
        ) : (
          <g>
            <text x="690" y="445" fill={mutedColor} fontSize="10" fontFamily="monospace">
              [PULL-DOWN TO GND]
            </text>
          </g>
        )}

        {/* Notes (CHG-04) */}
        <rect x="60" y="540" width="420" height="90" fill={bgColor} stroke={strokeColor} strokeWidth="1.2" />
        <text x="75" y="565" fill={strokeColor} fontSize="11" fontWeight="bold" fontFamily="monospace">
          FABRICATION & STACKUP SPECIFICATION:
        </text>
        <text x="75" y="590" fill={revision === 'B' ? '#D97706' : mutedColor} fontSize="10" fontFamily="monospace">
          {revision === 'A'
            ? '1. Standard FR4 4-Layer 1.6mm 1oz Cu.'
            : '1. Isola 370HR / Rogers 4350B Hybrid 4-Layer (Controlled 100Ω Diff)'}
        </text>
        <text x="75" y="610" fill={mutedColor} fontSize="10" fontFamily="monospace">
          2. RoHS 3 (2015/863/EU) Lead-Free ENIG Finish.
        </text>
      </svg>
    );
  }

  // Default: Precision Mechanical Lathe Spindle Flange Housing (ISO 2768)
  return (
    <svg
      viewBox="0 0 1000 700"
      className="w-full h-full select-none"
      style={{ backgroundColor: bgColor }}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <pattern id="cad-grid" width="30" height="30" patternUnits="userSpaceOnUse">
          <path d="M 30 0 L 0 0 0 30" fill="none" stroke={gridColor} strokeWidth="0.5" />
        </pattern>
        <pattern id="cad-hatch-45" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="8" stroke={strokeColor} strokeWidth="0.75" opacity="0.35" />
        </pattern>
        <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill={dimensionColor} />
        </marker>
        <marker id="arrowhead-rev" markerWidth="8" markerHeight="6" refX="1" refY="3" orient="auto">
          <polygon points="8 0, 0 3, 8 6" fill={dimensionColor} />
        </marker>
      </defs>

      {/* Grid Canvas */}
      <rect width="1000" height="700" fill="url(#cad-grid)" />

      {/* Centerline (Dash-Dot) */}
      <line x1="100" y1="350" x2="900" y2="350" stroke={centerLineColor} strokeWidth="1" strokeDasharray="25,4,4,4" />
      <line x1="500" y1="80" x2="500" y2="620" stroke={centerLineColor} strokeWidth="1" strokeDasharray="25,4,4,4" />

      {/* Section Cross Section Hatching (Upper Half) */}
      <path
        d="M 280 200 L 400 200 L 400 260 L 620 260 L 620 220 L 720 220 L 720 350 L 680 350 L 680 270 L 450 270 L 450 350 L 280 350 Z"
        fill="url(#cad-hatch-45)"
        stroke="none"
      />
      <path
        d="M 280 500 L 400 500 L 400 440 L 620 440 L 620 480 L 720 480 L 720 350 L 680 350 L 680 430 L 450 430 L 450 350 L 280 350 Z"
        fill="url(#cad-hatch-45)"
        stroke="none"
      />

      {/* Main Flange Geometry Profile */}
      <g stroke={strokeColor} strokeWidth="2.5" fill="none">
        {/* Left Flange Face */}
        <line x1="280" y1="200" x2="280" y2="500" />
        <line x1="280" y1="200" x2="400" y2="200" />
        <line x1="280" y1="500" x2="400" y2="500" />
        <line x1="400" y1="200" x2="400" y2="260" />
        <line x1="400" y1="500" x2="400" y2="440" />

        {/* Central Cylindrical Body */}
        <line x1="400" y1="260" x2="620" y2="260" />
        <line x1="400" y1="440" x2="620" y2="440" />
        <line x1="620" y1="260" x2="620" y2="220" />
        <line x1="620" y1="440" x2="620" y2="480" />

        {/* Right Stepped Hub (CHG-04: Chamfer vs Fillet) */}
        {revision === 'A' ? (
          <g>
            {/* 2x45 Chamfer */}
            <line x1="620" y1="220" x2="705" y2="220" />
            <line x1="705" y1="220" x2="720" y2="235" stroke="#E11D48" strokeWidth="2.5" />
            <line x1="720" y1="235" x2="720" y2="465" />
            <line x1="720" y1="465" x2="705" y2="480" stroke="#E11D48" strokeWidth="2.5" />
            <line x1="705" y1="480" x2="620" y2="480" />
          </g>
        ) : (
          <g>
            {/* R1.5 Fillet Radius */}
            <line x1="620" y1="220" x2="710" y2="220" />
            <path d="M 710 220 Q 720 220 720 230" stroke="#059669" strokeWidth="2.5" />
            <line x1="720" y1="230" x2="720" y2="470" />
            <path d="M 720 470 Q 720 480 710 480" stroke="#059669" strokeWidth="2.5" />
            <line x1="710" y1="480" x2="620" y2="480" />
          </g>
        )}

        {/* Internal Bore (CHG-01: 45mm vs 48.5mm) */}
        {revision === 'A' ? (
          <g>
            <line x1="450" y1="270" x2="680" y2="270" strokeWidth="2" />
            <line x1="450" y1="430" x2="680" y2="430" strokeWidth="2" />
            <line x1="450" y1="270" x2="450" y2="430" strokeWidth="2" />
            <line x1="680" y1="270" x2="680" y2="350" strokeWidth="2" />
            <line x1="680" y1="350" x2="680" y2="430" strokeWidth="2" />
          </g>
        ) : (
          <g>
            {/* Enlarged Bore */}
            <line x1="450" y1="255" x2="680" y2="255" stroke="#D97706" strokeWidth="2.5" />
            <line x1="450" y1="445" x2="680" y2="445" stroke="#D97706" strokeWidth="2.5" />
            <line x1="450" y1="255" x2="450" y2="445" stroke="#D97706" strokeWidth="2.5" />
            <line x1="680" y1="255" x2="680" y2="445" stroke="#D97706" strokeWidth="2.5" />
          </g>
        )}

        {/* Mounting Bolt Holes (PCD 110) */}
        <circle cx="340" cy="245" r="12" fill={bgColor} stroke={strokeColor} strokeWidth="1.5" />
        <circle cx="340" cy="455" r="12" fill={bgColor} stroke={strokeColor} strokeWidth="1.5" />
      </g>

      {/* Grease Port (CHG-02: Rev B Addition) */}
      {revision === 'B' && (
        <g>
          <rect x="485" y="180" width="30" height="80" fill={bgColor} stroke="#059669" strokeWidth="2" />
          <path d="M 485 200 L 515 200 M 485 220 L 515 220" stroke="#059669" strokeWidth="1" />
          <text x="500" y="165" fill="#059669" fontSize="11" fontWeight="bold" fontFamily="monospace" textAnchor="middle">
            1x M6 GREASE PORT [NEW]
          </text>
        </g>
      )}

      {/* Dimension Callouts & Leader Lines */}
      {/* Bore Dimension (CHG-01) */}
      <g>
        <line x1="560" y1={revision === 'A' ? 270 : 255} x2="560" y2={revision === 'A' ? 430 : 445} stroke={dimensionColor} strokeWidth="1.2" markerStart="url(#arrowhead-rev)" markerEnd="url(#arrowhead)" />
        <rect x="525" y="335" width="70" height="24" fill={bgColor} stroke={dimensionColor} strokeWidth="0.75" rx="3" />
        <text x="560" y="351" fill={dimensionColor} fontSize="11" fontWeight="bold" fontFamily="monospace" textAnchor="middle">
          {revision === 'A' ? 'Ø 45.00' : 'Ø 48.50'}
        </text>
      </g>

      {/* Axial Shoulder Runout (CHG-03) */}
      <g transform="translate(630, 200)">
        <line x1="0" y1="0" x2="50" y2="-40" stroke={dimensionColor} strokeWidth="1" />
        <rect x="50" y="-55" width="130" height="26" fill={bgColor} stroke={dimensionColor} strokeWidth="1" rx="2" />
        <text x="115" y="-38" fill={dimensionColor} fontSize="11" fontWeight="bold" fontFamily="monospace" textAnchor="middle">
          {revision === 'A' ? '⌖ 0.05 | A | B' : '⌖ 0.02 | A | B (REV)'}
        </text>
      </g>

      {/* Surface Finish (CHG-06) */}
      <g transform="translate(320, 310)">
        <path d="M 0 0 L 15 -25 L 30 0 Z" fill="none" stroke={strokeColor} strokeWidth="1.2" />
        <line x1="15" y1="-25" x2="55" y2="-25" stroke={strokeColor} strokeWidth="1.2" />
        <text x="35" y="-30" fill={strokeColor} fontSize="10" fontFamily="monospace">
          {revision === 'A' ? 'Ra 3.2' : 'Ra 0.8 (GROUND)'}
        </text>
      </g>

      {/* Engineering Notes Block (CHG-05) */}
      <g transform="translate(80, 520)">
        <rect x="0" y="0" width="380" height="130" fill={bgColor} stroke={strokeColor} strokeWidth="1.2" />
        <rect x="0" y="0" width="380" height="26" fill={isDark ? '#1F1F1F' : '#E5E5E5'} />
        <text x="12" y="18" fill={strokeColor} fontSize="11" fontWeight="bold" fontFamily="monospace">
          GENERAL ENGINEERING NOTES (UNLESS NOTED):
        </text>
        <text x="12" y="46" fill={mutedColor} fontSize="10" fontFamily="monospace">
          1. MATERIAL: 42CrMo4 ALLOY STEEL FORGING.
        </text>
        <text x="12" y="66" fill={mutedColor} fontSize="10" fontFamily="monospace">
          2. ALL CORNERS R1.5 MIN UNLESS SPECIFIED.
        </text>
        <text x="12" y="86" fill={mutedColor} fontSize="10" fontFamily="monospace">
          3. TOLERANCES PER ISO 2768-mK.
        </text>
        <text x="12" y="108" fill={revision === 'B' ? '#D97706' : mutedColor} fontSize="10" fontWeight={revision === 'B' ? 'bold' : 'normal'} fontFamily="monospace">
          {revision === 'A'
            ? '4. STRESS RELIEVE AT 450°C FOR 2 HRS.'
            : '4. PLASMA NITRIDE CASE 0.3mm MIN, 58-62 HRC (REV B)'}
        </text>
      </g>

      {/* ISO Standard Title Block */}
      <g transform="translate(620, 520)">
        <rect x="0" y="0" width="300" height="130" fill={bgColor} stroke={strokeColor} strokeWidth="1.5" />
        <line x1="0" y1="32" x2="300" y2="32" stroke={strokeColor} strokeWidth="1" />
        <line x1="0" y1="65" x2="300" y2="65" stroke={strokeColor} strokeWidth="1" />
        <line x1="0" y1="95" x2="300" y2="95" stroke={strokeColor} strokeWidth="1" />
        <line x1="160" y1="65" x2="160" y2="130" stroke={strokeColor} strokeWidth="1" />

        <text x="12" y="22" fill={strokeColor} fontSize="12" fontWeight="bold" fontFamily="monospace">
          DWG-MECH-8842-B | SPINDLE FLANGE
        </text>
        <text x="12" y="52" fill={mutedColor} fontSize="10" fontFamily="monospace">
          DISCIPLINE: MECHANICAL / CNC TURNING
        </text>
        <text x="12" y="82" fill={mutedColor} fontSize="9" fontFamily="monospace">
          SCALE: 1:1 (METRIC)
        </text>
        <text x="172" y="82" fill={mutedColor} fontSize="9" fontFamily="monospace">
          SHEET 1 OF 1
        </text>
        <text x="12" y="115" fill={strokeColor} fontSize="10" fontFamily="monospace">
          ZONE: A1 - D8
        </text>
        <text x="172" y="116" fill={revision === 'B' ? '#D97706' : strokeColor} fontSize="12" fontWeight="bold" fontFamily="monospace">
          REV: {revision === 'A' ? 'REV A (BASE)' : 'REV B (INC)'}
        </text>
      </g>
    </svg>
  );
};
