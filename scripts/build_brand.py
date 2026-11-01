"""Generate the original Energy Costs SVG and transparent PNGs using only Python."""
from pathlib import Path
from math import cos, sin, pi, sqrt
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
TEAL = (15, 91, 99, 255)
GOLD = (255, 204, 79, 255)
WHITE = (255, 255, 255, 255)
BOLT = [(130, 31), (65, 137), (111, 137), (93, 217), (166, 108), (120, 108)]
ARC = [(185 + radius*cos(angle*pi/180), 182 + radius*sin(angle*pi/180))
       for radius, angles in [(23, range(45, 316, 5)), (15, range(315, 44, -5))]
       for angle in angles]
SHAPES = [
    ("circle", (128, 128, 128), TEAL),
    ("polygon", BOLT, WHITE),
    ("circle", (184, 182, 54), TEAL),
    ("circle", (184, 182, 46), GOLD),
    ("polygon", ARC, TEAL),
    ("polygon", [(157, 172), (186, 172), (186, 178), (157, 178)], TEAL),
    ("polygon", [(157, 185), (183, 185), (183, 191), (157, 191)], TEAL),
]


def svg():
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-labelledby="title">',
             '<title id="title">Energy Costs: electricity and money</title>']
    for kind, geometry, color in SHAPES:
        fill = '#%02x%02x%02x' % color[:3]
        if kind == 'circle':
            x, y, r = geometry
            parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>')
        else:
            points = ' '.join(f'{x:.3f},{y:.3f}' for x, y in geometry)
            parts.append(f'<polygon points="{points}" fill="{fill}"/>')
    return '\n'.join(parts + ['</svg>', ''])


def png(size):
    # Scanline rendering at 4x resolution; average premultiplied colors at edges.
    sample = 4
    width = size * sample
    scale = width / 256
    pixels = bytearray(width * width * 4)
    for kind, geometry, color in SHAPES:
        for y in range(width):
            ordinate = (y + 0.5) / scale
            if kind == 'circle':
                cx, cy, radius = geometry
                distance = radius*radius - (ordinate-cy)**2
                intersections = [] if distance <= 0 else [cx-sqrt(distance), cx+sqrt(distance)]
            else:
                intersections = []
                for (x1, y1), (x2, y2) in zip(geometry, geometry[1:] + geometry[:1]):
                    if min(y1, y2) <= ordinate < max(y1, y2):
                        intersections.append(x1 + (ordinate-y1)*(x2-x1)/(y2-y1))
                intersections.sort()
            for left, right in zip(intersections[::2], intersections[1::2]):
                a = max(0, int(left*scale + 0.5))
                b = min(width, int(right*scale + 0.5))
                offset = (y*width+a)*4
                pixels[offset:offset+(b-a)*4] = bytes(color)*(b-a)
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            offsets = [((y*sample+dy)*width+x*sample+dx)*4
                       for dy in range(sample) for dx in range(sample)]
            alpha = sum(pixels[i+3] for i in offsets)
            rgb = [round(sum(pixels[i+c]*pixels[i+3] for i in offsets)/alpha) if alpha else 0
                   for c in range(3)]
            raw.extend((*rgb, round(alpha/(sample*sample))))

    def chunk(name, data):
        return struct.pack('!I', len(data)) + name + data + struct.pack('!I', zlib.crc32(name+data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def main():
    brand = ROOT / 'custom_components/energy_costs/brand'
    brand.mkdir(parents=True, exist_ok=True)
    (ROOT / 'docs/icon.svg').write_text(svg())
    for name, size in [('icon.png', 256), ('icon@2x.png', 512)]:
        (brand / name).write_bytes(png(size))
        print(f'{name}: {size}×{size}')


if __name__ == '__main__':
    main()
