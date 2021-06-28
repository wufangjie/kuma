import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
plt.ion()


fig = plt.figure(figsize=(8, 8))
ax = fig.add_subplot(111)
plt.axis('equal')
plt.axis([-10, 10, -10, 10])
r = 3
ax.add_patch(Rectangle((-10, -10), 20, 20, fill=True, edgecolor='k', facecolor='k', alpha=0))
ax.add_patch(Rectangle((-10+r, -10), 20-2*r, 20, fill=True, edgecolor='k', facecolor='k'))
ax.add_patch(Rectangle((-10, -10+r), 20, 20-2*r, fill=True, edgecolor='k', facecolor='k'))
ax.add_patch(Circle((-10+r, -10+r), r, fill=True, facecolor='k'))
ax.add_patch(Circle((-10+r, 10-r), r, fill=True, facecolor='k'))
ax.add_patch(Circle((10-r, 10-r), r, fill=True, facecolor='k'))
ax.add_patch(Circle((10-r, -10+r), r, fill=True, facecolor='k'))
ax.add_patch(Circle((0, 0), 6, fill=True, facecolor='w'))
ax.add_patch(Circle((0, 0), 4, fill=True, facecolor='k'))
ax.add_patch(Rectangle((-1, 3), 2, 6, fill=True, facecolor='w'))
ax.add_patch(Rectangle((-1, -9), 2, 6, fill=True, facecolor='w'))
ax.add_patch(Rectangle((-9, -1), 6, 2, fill=True, facecolor='w'))
ax.add_patch(Rectangle((3, -1), 6, 2, fill=True, facecolor='w'))
ax.add_patch(Rectangle((-0.1, -10), 0.2, 20, fill=True, edgecolor='k', linewidth=2, facecolor='#666666'))
plt.gcf().subplots_adjust(bottom=0, top=1, left=0, right=1)
plt.axis('off')
for pixel in [64, 128, 256, 512]:
    print(pixel)
    plt.savefig('kuma({0}x{0}).png'.format(pixel), dpi=pixel//8, transparent=True)
