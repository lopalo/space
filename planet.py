from random import randint
from functools import wraps
from os import path
from math import hypot, atan, ceil, degrees
from itertools import combinations
from PyQt4.QtGui import *
from PyQt4.QtCore import QRectF, QPointF
from . import settings
from .space_objects import *
from .utils import Vect


def recalc_pairs(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        cls = self.__class__
        assert cls is Planet
        old_len = len(self.planets)
        ret = method(self, *args, **kwargs)
        if old_len != len(self.planets):
            cls.all_pairs = tuple(combinations(self.planets, 2))
        inter_planets = (pl for pl in self.planets if not pl.captured)
        cls.interacting_pairs = tuple(combinations(inter_planets, 2))
        return ret
    return wrapper


class Planet(QGraphicsPixmapItem):
    planets = list()
    all_pairs = tuple()
    interacting_pairs = tuple()
    effects = list()
    total_mass = 0

    captured = False
    bang = False

    @recalc_pairs
    def __init__(self, pixmap, image_name, radius=None,
                    position=None, speed=(0.0, 0.0), glow=False):
        if not self.check_adding(radius): return
        pixmap = pixmap.scaledToHeight(radius * 2)
        super(Planet, self).__init__(pixmap)
        self.image_name = image_name
        self.radius = radius or settings.default_radius
        self.position = position or list(settings.default_position)
        self.speed = Vect(*speed)
        self.glow = glow
        if glow:
            self.shadow_collection = []
        else:
            self.glow_collection = []
        self.planets.append(self)
        self.scene.addItem(self)
        self.setZValue(1 if glow else 2)
        self.set_position()
        self.update_total_mass()
        self.window.update_cursor()

    @recalc_pairs
    def delete(self):
        self.planets.remove(self)
        self.scene.removeItem(self)
        self.update_total_mass()
        self.window.update_cursor()

    @recalc_pairs
    def release(self):
        self.setZValue(self.saved_z_val)
        self.saved_z_val = None
        self.captured = False
        self.prev_capt_pos = None
        self.speed = self.capt_speed.clone()
        self.capt_speed = None
        self.scene.hot_keys_enabled = True

    @recalc_pairs
    def capture(self):
        self.saved_z_val = self.zValue()
        self.setZValue(10)
        self.speed = Vect(0.0, 0.0)
        self.prev_capt_pos = tuple(self.position)
        self.captured = True
        self.scene.hot_keys_enabled = False

    @classmethod
    def update_total_mass(cls):
        cls.total_mass = tm = int(ceil(sum((pl.mass for pl in cls.planets))))
        text = 'total mass: {0} / {1}'.format(tm, settings.max_mass)
        cls.window.total_mass_label.setText(text)

    @classmethod
    def setup(cls, window, scene):
        cls.window = window
        cls.scene = scene

    @classmethod
    def set_max_pos(cls, max_x, max_y):
        cls.max_x = max_x
        cls.max_y = max_y

    @classmethod
    def action_loop(cls, time_delta):
        #print('effects count: ', len(cls.effects))
        #print('planets count: ', len(cls.planets))
        #print('inter pairs count: ', len(list(cls.interacting_pairs)))
        #print('all pairs count: ', len(list(cls.all_pairs)))
        cls.time_delta = time_delta
        cls.run_effects()
        cls.update_forces()
        cls.update_speeds()
        cls.update_positions()
        cls.collect_glow()
        cls.repaint()

    @property
    def mass(self):
        return self.radius * settings.density

    @property
    def acceleration(self):
        return self.force / self.mass

    @property
    def glow_rate(self):
        f = 4 if self.bang else 1
        return self.radius * settings.glow_factor * f if self.glow else None

    def get_vector(self, other):
        x = other.position[0] - self.position[0]
        y = other.position[1] - self.position[1]
        return Vect(x, y)

    @classmethod
    def update_forces(cls):
        for pl in cls.planets:
            pl.force = Vect(0.0, 0.0)
        for pl1, pl2 in cls.interacting_pairs:
            vect = pl1.get_vector(pl2)
            if vect.len == 0: continue
            G = settings.G
            F = G * pl1.mass * pl2.mass / vect.len**2
            vect.len = F
            pl1.force = pl1.force + vect / 2
            pl2.force = pl2.force + vect.reverse() / 2

    @classmethod
    def update_speeds(cls):
        for pl in cls.planets:
            pl.speed += pl.acceleration * cls.time_delta

    @classmethod
    def update_positions(cls):
        for pl in cls.planets:
            pl.set_position()
        cls.check_collisions()

    def set_position(self):
        td = self.time_delta
        pos_delta = self.speed * td
        self.position[0] += pos_delta.x
        self.position[1] += pos_delta.y
        self.setPos(
            int(self.position[0] - self.radius),
            int(self.position[1] - self.radius)
        )

        if self.captured:
            factor = settings.captured_speed_factor
            self.capt_speed = Vect(
                (self.position[0] - self.prev_capt_pos[0]),
                (self.position[1] - self.prev_capt_pos[1])
            ) / factor / td
            self.prev_capt_pos = tuple(self.position)

        #reflect from borders
        if self.captured: return
        x_left = self.radius
        x_right = self.max_x - self.radius
        y_top = self.radius
        y_bottom = self.max_y - self.radius
        pos, s = self.position, self.speed
        f = settings.reflect_factor
        if pos[0] < x_left:
            if s.x == 0: s.x = 10
            elif s.x < 0:
                s.x = -s.x * f
                s.y = s.y * f
        if pos[0] > x_right:
            if s.x == 0: s.x = 10
            elif s.x > 0:
                s.x = -s.x * f
                s.y = s.y * f
        if pos[1] < y_top:
            if s.y == 0: s.y = 10
            elif s.y < 0:
                s.y = -s.y * f
                s.x = s.x * f
        if pos[1] > y_bottom:
            if s.y == 0: s.y = 10
            elif s.y > 0:
                s.y = -s.y * f
                s.x = s.x * f

    @classmethod
    def check_collisions(cls):
        from .space import Pixmap

        check = True
        while check:
            for pl1, pl2 in cls.interacting_pairs:
                min_dist = pl1.radius + pl2.radius
                pos1, pos2 = pl1.position, pl2.position
                dist = hypot(pos2[0] - pos1[0], pos2[1] - pos1[1])

                #processing collision
                if dist < min_dist:
                    imp1 = pl1.speed.clone() * pl1.mass
                    imp2 = pl2.speed.clone() * pl2.mass
                    heavier = max(pl1, pl2, key=lambda x: x.mass)
                    lighter = min(pl1, pl2, key=lambda x: x.mass)
                    k_mass = heavier.mass / lighter.mass
                    if k_mass <= 2:
                        pos = [(pos1[0] + pos2[0]) / 2, (pos1[1] + pos2[1]) / 2]
                    else:
                        pos = heavier.position
                    imp = (imp1 + imp2) * 0.81
                    pl1.delete()
                    pl2.delete()
                    img_name = settings.collided_image
                    pixmap = Pixmap(path.join(
                        settings.planet_images_path,
                        img_name
                    ))
                    r = min_dist * 0.9
                    new_planet = cls(pixmap, img_name, r, pos, glow=True)
                    speed = imp / new_planet.mass
                    new_planet.speed = speed
                    new_planet.bang = True
                    def callback():
                        new_planet.bang = False
                    cls.make_explosion(pos, min_dist * 3, callback)
                    break
            else:
                check = False

    def merge(self):
        from .space import Pixmap

        for other in self.planets:
            if other is self: continue
            pos1, pos2 = self.position, other.position
            dist = hypot(pos2[0] - pos1[0], pos2[1] - pos1[1])
            if self.radius + other.radius > dist:
                if self.radius > other.radius:
                    image_name = self.image_name
                else:
                    image_name = other.image_name
                end_px = Pixmap(path.join(
                    settings.planet_images_path, image_name
                ))
                start_px = Pixmap(path.join(
                    settings.planet_images_path, other.image_name
                ))
                other.image_name = image_name
                r = self.radius + other.radius
                eff = PlanetMerging(other, start_px, end_px, other.radius, r)
                self.delete()
                self.make_collapsing()
                self.effects.append(eff)
                break

    def _break(self):
        from .space import Pixmap

        direction = randint(0, 360)
        b_speed = settings.break_speed
        b_speed = Vect.create(b_speed, direction)
        speed = self.speed / 2
        speed1 = speed + b_speed
        speed2 = speed - b_speed
        radius = self.radius / 2
        pos = Vect(*self.position)
        length = radius + 1
        pos_offset = Vect.create(length, direction)
        pos1 = list((pos + pos_offset).coord)
        pos2 = list((pos - pos_offset).coord)
        image_name = self.image_name
        pixmap = Pixmap(path.join(
            settings.planet_images_path, image_name
        ))
        glow = self.glow
        self.delete()
        cls = self.__class__
        cls(pixmap, image_name, radius, pos1, speed1.coord, glow)
        cls(pixmap, image_name, radius, pos2, speed2.coord, glow)


    def boundingRect(self):
        r1 = self.radius
        r2 = settings.glow_radius
        return QRectF(r1 - r2, r1 - r2, r2 * 2, r2 * 2)

    @classmethod
    def collect_glow(cls):
        for pl1, pl2 in cls.all_pairs:
            if pl1.glow and pl2.glow: continue
            if not pl1.glow and not pl2.glow: continue
            pos1, pos2 = pl1.position, pl2.position
            dist = hypot(pos2[0] - pos1[0], pos2[1] - pos1[1])
            if pl1.radius + pl2.radius > dist: continue

            glow, pl = (pl1, pl2) if pl1.glow else (pl2, pl1)
            if glow.captured: continue
            vect = pl.get_vector(glow)
            gr = settings.glow_radius
            rate = min(max(1 - vect.len / gr, 0) * glow.glow_rate, 1)
            pl.glow_collection.append((rate, vect))

            #collect info for painting the shadows
            if gr < dist or not settings.on_shadows: continue
            info = []
            vect = vect.reverse()
            r = pl.radius
            k = degrees(atan(r / vect.len))
            info.extend([-(vect.angle - k), -2*k])
            for angle in (-90, 90):
                v = vect.clone()
                v.len = r
                v.rotate(angle)
                info.append((v + vect + Vect(gr, gr)).coord)
            glow.shadow_collection.append(info)

    def paint(self, painter, option, widget):
        r = self.radius
        if not self.captured and self.glow and settings.on_shadows:
            gr = settings.glow_radius
            img = QImage(gr * 2, gr * 2, 6)
            img.fill(0)
            ipainter = QPainter(img)
            grad = QRadialGradient(gr, gr, gr)
            alpha = int(self.radius / settings.max_planet_radius
                                            * 4 if self.bang else 1) * 50
            grad.setColorAt(0, QColor(255, 166, 0, min(alpha, 255)))
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            brush = QBrush(grad)
            ipainter.setBrush(brush)
            ipainter.setPen(QColor(0, 0, 0, 0))
            ipainter.drawEllipse(0, 0, gr * 2, gr * 2)
            ipainter.setCompositionMode(7)
            for fangle, sl, fp, sp in self.shadow_collection:
                path = QPainterPath(QPointF(*fp))
                path.arcTo(0, 0, gr * 2, gr * 2, fangle, sl)
                path.lineTo(*sp)
                path.lineTo(*fp)
                ipainter.fillPath(path, QBrush(QColor(0, 0, 0, 0)))
            ipainter.end()
            painter.drawImage(r - gr, r - gr, img)
            self.shadow_collection = []

        super(Planet, self).paint(painter, option, widget)

        if not self.glow:
            for rate, vect in self.glow_collection:
                r_vect = Vect(r, r)
                vect.len = r
                vect += r_vect
                x, y = vect.coord
                alpha = int(255 * rate)
                grad = QRadialGradient(x, y, r * 2)
                grad.setColorAt(0, QColor(255, 166, 0, alpha))
                grad.setColorAt(0.7, QColor(0, 0, 0, 0))
                brush = QBrush(grad)
                painter.setBrush(brush)
                painter.setPen(QColor(0, 0, 0, 0))
                painter.drawEllipse(0, 0, r * 2, r * 2)
            self.glow_collection = []
        self.draw_atmosphere(painter)

    def draw_atmosphere(self, painter, pos=None):
        r = self.radius
        r_atm = r * 1.1
        if pos is None:
            pos = r - r_atm
        color = QColor(self.pixmap().toImage().scaledToWidth(1).pixel(0, 0))
        color.setAlpha(200)
        grad = QRadialGradient(r_atm + pos, r_atm + pos, r_atm)
        grad.setColorAt(0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.7, QColor(0, 0, 0, 0))
        grad.setColorAt(0.9, color)
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        brush = QBrush(grad)
        painter.setBrush(brush)
        painter.setPen(QColor(0, 0, 0, 0))
        painter.drawEllipse(pos, pos, r_atm * 2, r_atm * 2)

    @classmethod
    def repaint(cls):
        for pl in cls.planets:
            pl.update()

    @classmethod
    def check_adding(cls, radius):
        if radius * settings.density + cls.total_mass < settings.max_mass:
            return True
        return False

    @classmethod
    def make_explosion(cls, pos, radius, callback):
        comp_count = settings.bang_components_count
        expl = Explosion(cls.scene, pos, radius, callback, comp_count)
        cls.effects.append(expl)

    def make_collapsing(self, callback=None):
        coll = Collapsing(self.scene, self.pixmap(), self.position, callback)
        self.effects.append(coll)

    @classmethod
    def make_inflation(cls, pixmap, radius, pos, callback=None):
        if not cls.check_adding(radius): return
        pixmap = pixmap.scaledToHeight(radius * 2)
        infl = Inflation(cls.scene, pixmap, pos, callback)
        cls.effects.append(infl)

    @classmethod
    def run_effects(cls):
        for eff in cls.effects:
            assert isinstance(eff, Effect)
            eff.run(cls.time_delta)
            if eff.finished:
                cls.effects.remove(eff)
                eff.callback()

    def mousePressEvent(self, event):
        if self.window.action is None:
            self.capture()
            point = event.scenePos()
            self.position = [point.x(), point.y()]
        elif self.window.action == 'del':
            self.delete()
            self.make_collapsing()
        elif self.window.action == 'break':
            self._break()

    def mouseReleaseEvent(self, event):
        if not self.window.action is None: return
        self.merge()
        self.release()

    def mouseMoveEvent(self, event):
        if self.captured:
            point = event.scenePos()
            self.position = [point.x(), point.y()]

    def to_dict(self):
        return {
            'image_name': self.image_name,
            'radius': self.radius,
            'position': self.position,
            'speed': self.speed.coord,
            'glow': self.glow
        }
