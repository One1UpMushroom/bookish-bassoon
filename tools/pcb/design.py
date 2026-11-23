"""The task lamp driver board, as data.

This file is the single description of the circuit. The schematic generator
(gen_sch.py) and the board generator (gen_pcb.py) both read it, and check.py
compares what KiCad extracts from each of them against it, so the drawing, the
copper and this list cannot drift apart.

Each part: reference, value, schematic symbol, footprint, {pin number: net},
where it comes from, and a one-line note for the bill of materials.
"""

SYM_QTPY = 'TaskLamp:QTPy_RP2040'
FP_QTPY = 'TaskLamp:QTPy_RP2040_Socket'

FP_R = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
FP_D41 = 'Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal'
FP_D201 = 'Diode_THT:D_DO-201AD_P15.24mm_Horizontal'
FP_D15 = 'Diode_THT:D_DO-15_P12.70mm_Horizontal'
FP_TO220 = 'Package_TO_SOT_THT:TO-220-3_Vertical'
FP_HSOIC = 'TaskLamp:HSOIC-8-1EP_HandSolder_BackHole'
FP_L7 = 'TaskLamp:L_Bourns_SRP7028A_HandSolder'
FP_C1210 = 'TaskLamp:C_1210_HandSolder'
FP_CCHIP = 'TaskLamp:C_0805-1206_HandSolder'
FP_RCHIP = 'TaskLamp:R_0805-1206_HandSolder'
FP_CDUAL = 'TaskLamp:C_Dual_THT-P5.08_or_0805-1206'
FP_FUSE = 'Fuse:Fuseholder_Blade_Mini_Keystone_3568'
FP_TB = 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-%d-5.08_1x%02d_P5.08mm_Horizontal'
FP_HDR8 = 'Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical'
FP_CP8 = 'Capacitor_THT:CP_Radial_D8.0mm_P3.50mm'
FP_CP5 = 'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm'
FP_C = 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'
FP_TP = 'TestPoint:TestPoint_THTPad_D2.0mm_Drill1.0mm'
FP_HOLE = 'MountingHole:MountingHole_3.2mm_M3'

STOCK = 'stock'   # already in the component inventory
ORDER = 'order'   # on the shopping list (docs/parts-to-order.md)

# Channel order everywhere: R, G, B, warm white, cool white.
CHANNELS = ['R', 'G', 'B', 'WW', 'CW']
CHANNEL_NAMES = {'R': 'red', 'G': 'green', 'B': 'blue', 'WW': 'warm white', 'CW': 'cool white'}

# QT Py pads, numbered like a DIP seen from above with the USB socket at the
# top: 1-7 down the left side, 8-14 up the right side.
QTPY_PINS = {
    '1': ('A0', 'PWM_R'),
    '2': ('A1', 'PWM_G'),
    '3': ('A2', 'PWM_B'),
    '4': ('A3', 'PWM_WW'),
    '5': ('SDA', 'TFT_CS'),
    '6': ('SCL', 'TFT_DC'),
    '7': ('TX', 'PWM_CW'),
    '8': ('RX', 'TFT_LITE'),
    '9': ('SCK', 'TFT_SCK'),
    '10': ('MI', 'ENC_INT'),
    '11': ('MO', 'TFT_MOSI'),
    '12': ('3V', '+3V3'),
    '13': ('GND', 'GND'),
    '14': ('5V', 'QT_5V'),
}

# Display / encoder header, top to bottom on the board.
J4_PINS = ['+3V3', 'TFT_MOSI', 'ENC_INT', 'TFT_SCK', 'TFT_LITE', 'TFT_CS', 'TFT_DC', 'GND']
J4_LABELS = ['3V', 'MOSI', 'INT', 'SCK', 'LITE', 'CS', 'DC', 'GND']


def parts():
    p = []

    def add(ref, value, sym, fp, pins, src, note, mpn=''):
        p.append(dict(ref=ref, value=value, sym=sym, fp=fp, pins=pins, src=src, note=note, mpn=mpn))

    # --- 24 V input: terminal -> fuse -> reverse-polarity diode -> rail
    add('J1', '24V IN', 'Connector:Screw_Terminal_01x02', FP_TB % (2, 2),
        {'1': 'GND', '2': 'VIN'}, ORDER, '24 V supply input, 5.08 mm screw terminal', 'OSTTC022162')
    add('F1', '2A mini blade', 'Device:Fuse', FP_FUSE,
        {'1': 'VFUSE', '2': 'VIN'}, ORDER, 'Mini (ATM) blade fuse holder with a 2 A fuse', '3568 + 0297002.WXNV')
    add('D7', 'SB560', 'Device:D_Schottky', FP_D201,
        {'1': '+24V', '2': 'VFUSE'}, ORDER, 'Reverse-polarity protection, 60 V 5 A Schottky', 'SB560-E3/54')
    add('D8', 'P6KE30A', 'Device:D_Zener', FP_D15,
        {'1': '+24V', '2': 'GND'}, ORDER, 'Surge clamp (TVS) across the 24 V rail', 'P6KE30A')
    add('C1', '100uF 50V', 'Device:C_Polarized', FP_CP8,
        {'1': '+24V', '2': 'GND'}, STOCK, 'Bulk capacitor at the input')
    add('C2', '100uF 50V', 'Device:C_Polarized', FP_CP8,
        {'1': '+24V', '2': 'GND'}, STOCK, 'Bulk capacitor beside the strip terminals')

    # --- 5 V supply for the controller: an LMR33630 buck converter, set for 5.0 V
    # (the circuit of the BUCK//33630 breakout, branch Branchy). EN is tied to VIN, PG unused.
    add('U2', 'LMR33630ADDAR', 'Regulator_Switching:LMR33630ADDA', FP_HSOIC,
        {'1': 'GND', '2': '+24V', '3': '+24V', '5': 'FB', '6': 'VCC', '7': 'BOOT', '8': 'SW', '9': 'GND'},
        ORDER, '24 V to 5 V buck converter, 3 A, 400 kHz', 'LMR33630ADDAR')
    add('L1', '10uH', 'Device:L', FP_L7, {'1': 'SW', '2': '+5V'}, ORDER,
        'Buck inductor, shielded, Isat 6 A', 'SRP7028A-100M')
    add('C3', '10uF 50V', 'Device:C', FP_C1210, {'1': 'GND', '2': '+24V'}, ORDER,
        'Buck input capacitor, X7R', 'GRM32ER71H106KA12L')
    add('C4', '10uF 50V', 'Device:C', FP_C1210, {'1': '+24V', '2': 'GND'}, ORDER,
        'Buck input capacitor, X7R', 'GRM32ER71H106KA12L')
    add('C5', '220nF 50V', 'Device:C', FP_CCHIP, {'1': 'GND', '2': '+24V'}, ORDER,
        'Buck input bypass, X7R 0805 or 1206', 'C0805C224K5RACTU')
    add('C6', '100nF', 'Device:C', FP_CDUAL, {'1': 'SW', '2': 'BOOT'}, STOCK,
        'Bootstrap capacitor (radial, or a chip on the inner pads)')
    add('C7', '1uF', 'Device:C', FP_CDUAL, {'1': 'VCC', '2': 'GND'}, STOCK,
        'Buck VCC capacitor (radial, or a chip on the inner pads)')
    for ref, pins in (('C8', {'1': '+5V', '2': 'GND'}), ('C9', {'1': '+5V', '2': 'GND'}),
                      ('C10', {'1': 'GND', '2': '+5V'}), ('C11', {'1': 'GND', '2': '+5V'})):
        add(ref, '22uF 25V', 'Device:C', FP_C1210, pins, ORDER, 'Buck output capacitor, X7R', 'GRM32ER71E226KE15L')
    add('R11', '100k 1%', 'Device:R', FP_RCHIP, {'1': 'FB', '2': '+5V'}, ORDER,
        'Feedback divider, top (0805 or 1206)', 'RC1206FR-07100KL')
    add('R12', '24.9k 1%', 'Device:R', FP_RCHIP, {'1': 'GND', '2': 'FB'}, ORDER,
        'Feedback divider, bottom: 5.02 V out (0805 or 1206)', 'RC1206FR-0724K9L')
    add('D6', '1N5819', 'Diode:1N5819', FP_D41,
        {'1': 'QT_5V', '2': '+5V'}, STOCK, 'Feeds the QT Py 5V pad; lets USB be plugged in at the same time')

    # --- Controller
    add('U1', 'QT Py RP2040', SYM_QTPY, FP_QTPY,
        {n: net for n, (_, net) in QTPY_PINS.items()}, ORDER,
        'Adafruit QT Py RP2040 on two 1x7 sockets (the board itself is on hand)', '2x PPTC071LFBN-RC')
    add('J4', 'DISPLAY', 'Connector:Conn_01x08_Pin', FP_HDR8,
        {str(i + 1): net for i, net in enumerate(J4_PINS)}, STOCK,
        'Pin header to the TFT and the encoder INT pad')

    # --- Five identical strip switches
    for i, ch in enumerate(CHANNELS):
        n = i + 1
        name = CHANNEL_NAMES[ch]
        add('R%d' % n, '220', 'Device:R', FP_R,
            {'1': 'PWM_' + ch, '2': 'GATE_' + ch}, STOCK, 'Gate resistor, %s' % name)
        add('R%d' % (n + 5), '100k', 'Device:R', FP_R,
            {'1': 'GND', '2': 'GATE_' + ch}, STOCK, 'Gate pull-down, %s' % name)
        add('Q%d' % n, 'IRLB8721', 'Transistor_FET:IRLB8721PBF', FP_TO220,
            {'1': 'GATE_' + ch, '2': 'OUT_' + ch, '3': 'GND'}, STOCK, 'Strip switch, %s' % name)
        add('D%d' % n, '1N5819', 'Diode:1N5819', FP_D41,
            {'1': '+24V', '2': 'OUT_' + ch}, STOCK, 'Clamp for the strip wiring, %s' % name)

    # --- Strip terminals
    add('J3', 'RGB STRIP', 'Connector:Screw_Terminal_01x04', FP_TB % (4, 4),
        {'1': '+24V', '2': 'OUT_R', '3': 'OUT_G', '4': 'OUT_B'}, ORDER,
        'RGB strip: +24 V, red, green, blue', 'OSTTC042162')
    add('J2', 'WHITE STRIP', 'Connector:Screw_Terminal_01x03', FP_TB % (3, 3),
        {'1': '+24V', '2': 'OUT_WW', '3': 'OUT_CW'}, ORDER,
        'Tunable-white strip: +24 V, warm, cool', 'OSTTC032162')

    # --- Test pads and mounting holes
    add('TP1', '+5V', 'Connector:TestPoint', FP_TP, {'1': '+5V'}, '', 'Test pad')
    add('TP2', 'GND', 'Connector:TestPoint', FP_TP, {'1': 'GND'}, '', 'Test pad')
    for n in range(1, 5):
        add('H%d' % n, 'M3', 'Mechanical:MountingHole', FP_HOLE, {}, '', 'Mounting hole, 3.2 mm')
    return p


def netlist():
    """{net name: sorted list of 'REF.pin'} for every pin of every part."""
    nets = {}
    for part in parts():
        for pin, net in part['pins'].items():
            nets.setdefault(net, []).append('%s.%s' % (part['ref'], pin))
    return {k: sorted(v) for k, v in nets.items()}


if __name__ == '__main__':
    ps = parts()
    print('%d parts, %d nets' % (len(ps), len(netlist())))
    for net, pins in sorted(netlist().items()):
        print('  %-9s %s' % (net, ' '.join(pins)))
