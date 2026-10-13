"""Reader-facing oracle summaries, checked against the ACL appendix.

Names and full laws are always read from the current paper. This catalogue
specifies how to make each law observable in a newly scripted demonstration.
"""
import json
from pathlib import Path
from paper_scenes import paper_scene_names, paper_scene_laws

CATALOG = {
 '01':dict(formula='Same conditions → same motion',condition='A ball is on the decorative gray tile.',effect='Nothing extra happens. The tile is an ordinary-physics control.',scope='Gravity, inertia, friction and collisions remain ordinary.',signal='height',measure='Ball height',unit='bricks'),
 '02':dict(formula='F = 20 / r²  (r ≥ 0.5)',condition='Two free red spheres are near one another.',effect='They attract along the line joining them. Blue spheres do not participate.',scope='Below r = 0.5, the force uses the capped-distance formula in the full oracle. Added free red spheres are included.',signal='force',measure='Attractive force',unit='force units'),
 '03':dict(formula='a = g₀ √(1 / m)',condition='Free bodies with different masses are released together.',effect='The mass-4 blue ball falls with half the acceleration of mass-1 red.',scope='All free bodies, including added ones. Equal impulse is not equal initial speed.',signal='height',measure='Ball height',unit='bricks'),
 '04':dict(formula='g(t) = g₀[1 + 0.3 sin(2πt/6)]',condition='The same launch is repeated at different times.',effect='Gravity oscillates from 0.7g₀ to 1.3g₀ with a six-count period.',scope='The change is global and continuous during each flight.',signal='gravity',measure='Gravity / g₀',unit='ratio'),
 '05':dict(formula='F = −8 (s − 2.5) v / s',condition='An original ball or box moves faster than s = 2.5.',effect='An extra brake opposes its velocity. The brake vanishes at or below 2.5.',scope='The same speed threshold applies everywhere. Ordinary friction also acts.',signal='speed',measure='Red ball speed',unit='bricks/count'),
 '06':dict(formula='F = 1.2 (vᵧ, −vₓ, 0)',condition='Red or blue is moving horizontally.',effect='A force to the right of motion turns the path clockwise.',scope='The force is perpendicular to velocity and does no work. It is not a fixed compass-direction force.',signal='side_force',measure='Northward force Fᵧ',unit='force units'),
 '07':dict(formula='v↑ = 0.90 |v↓|  /  0.15 |v↓|',condition='A new downward floor impact occurs on a colored tile.',effect='Red returns 90% of the vertical speed; blue returns only 15%.',scope='The rule follows the surface. Gray balls and movable apparatus parts are included.',signal='vertical_speed',measure='Vertical velocity',unit='bricks/count'),
 '08':dict(formula='p = m v / (1 − |v|² / 2.2²)',condition='A force or impulse adds momentum to a free body.',effect='More impulse yields diminishing speed gains. Speed stays below 2.2.',scope='The limit also applies to free fall and added free bodies.',signal='speed',measure='Blue ball speed',unit='bricks/count'),
 '09':dict(formula='Enter: v × 0.4   ·   Exit: v × 2.5',condition='Red or blue crosses the gray tile’s horizontal boundary.',effect='Velocity jumps down on entry and up on exit, even above the tile.',scope='Linear and angular velocity are affected. Exit scales the remaining velocity, not the original entry velocity.',signal='speed',measure='Red ball speed',unit='bricks/count'),
 '10':dict(formula='Seed: vₓ = 0.35 · Gain: ×1.0015',condition='Red or blue lies inside the yellow footprint, at any height.',effect='The world injects motion: an eastward seed at low speed, amplification below speed 6.',scope='Updates occur each physics step. Ordinary forces remain active, so net speed need not increase every instant.',signal='energy',measure='Energy added by the oracle',unit='energy units'),
 '11':dict(formula='At separation: vafter = 1.8 vbefore',condition='Contact between two experiment balls ends.',effect='Both participants’ remaining linear velocities are multiplied by 1.8.',scope='The third ball is unchanged. Floor, wall and apparatus contacts do not trigger this gain.',signal='speed',measure='Blue ball speed',unit='bricks/count'),
 '12':dict(formula='(color A, color B) → (color B, color A)',condition='Two free single-sphere bodies begin a new contact.',effect='Their colors swap once. Their object identities do not swap.',scope='Sustained contact does not repeat the swap. Separation followed by renewed contact does.',signal='color',measure='Object color through time',unit='identity'),
 '13':dict(formula='Every third contact: v_z ← 4',condition='The original red–blue pair makes its third distinct contact.',effect='Both receive an upward kick. The count then continues to the next third contact.',scope='Sustained contact counts once. Wall, floor and added-ball contacts do not increment this counter.',signal='height',measure='Red ball height',unit='bricks'),
 '14':dict(formula='vgreen(t + 12) ← vred(t⁺)',condition='A nonzero push or throw launches the original red ball.',effect='Twelve counts later, green’s linear velocity is replaced by the stored value.',scope='Holding red does not cancel the event. This is replacement, not added velocity or path replay.',signal='speed',measure='Green ball speed',unit='bricks/count'),
 '15':dict(formula='Fᵧ = 1.5m · Launch pauses 10 counts',condition='Any movable object receives a nonzero push or throw.',effect='Red’s northward force pauses for ten counts. Another launch resets the timer.',scope='Zero impulses, building and hand movement do not reset it. The force starts active and resumes after the pause.',signal='force',measure='Red’s extra northward force',unit='force units')
}

PLAIN = {
 '01':('The gray tile does not change how objects move.','灰色地砖不会改变物体的运动。'),
 '02':('Red balls attract each other; blue balls do not.','红球互相吸引，蓝球不参与。'),
 '03':('The heavier blue ball falls more slowly than the lighter red one.','重的蓝球反而比轻的红球落得慢。'),
 '04':('Gravity gets stronger and weaker in a six-second cycle.','重力每六秒完成一次由强到弱、再变强的循环。'),
 '05':('Fast-moving objects get an extra brake; slow ones do not.','物体速度够快时会受到额外制动，慢下来就没有了。'),
 '06':('Moving balls are pushed sideways to their right.','球运动时，总会受到一个朝自身右侧的力。'),
 '07':('Identical balls bounce high on red tiles and low on blue tiles.','一样的球，在红地砖上弹得高，在蓝地砖上弹得低。'),
 '08':('Push harder, and speed approaches a limit it can never reach.','推得再用力，速度也只能接近一个永远达不到的上限。'),
 '09':('Balls slow down on entering the gray tile and speed up on leaving it.','球进入灰色区域就减速，离开时就加速。'),
 '10':('Either ball gains extra motion inside yellow, even in the air.','红球、蓝球进入黄色区都会获得助推，在空中也有效。'),
 '11':('When two balls separate after a collision, both get a speed boost.','两球碰撞后分开时，都会获得一次额外加速。'),
 '12':('When two balls touch, they swap colors.','两个球一接触，就交换颜色。'),
 '13':('Every third collision between the two balls makes both jump.','两球每相撞三次，就一起向上跳一下。'),
 '14':('Push red, and twelve seconds later green copies its launch speed and direction.','推动红球十二秒后，绿球会获得红球刚被推动时的速度和方向。'),
 '15':('Red is pulled north, but pushing any object pauses that pull for ten seconds.','红球受到向北的拉力，但推动任意物体都会让这股力暂停十秒。')
}

# Edited explanations for the page; the complete paper laws remain in `law`.
EXPLAIN = {
 '01':('The gray tile follows ordinary physics.','Ordinary contact is simplified.'),
 '02':('Free red spheres attract; blue spheres are unaffected. The force calculation uses a minimum distance of 0.5.','Equal masses; friction omitted.'),
 '03':('Heavier free bodies fall more slowly. A mass-4 ball accelerates downward half as fast as a mass-1 ball.','Vertical flight; rebounds omitted.'),
 '04':('Gravity cycles between 0.7 and 1.3 times its usual strength every six seconds.','Exact gravity cycle; contact simplified.'),
 '05':('Red, blue, and the box get extra braking above speed 2.5. It switches off at or below 2.5.','Extra braking only; friction omitted.'),
 '06':('Red and blue feel a force to the right of their horizontal motion. Its direction changes with their motion.','Side force only; friction omitted.'),
 '07':('At impact, red tiles return 90% of vertical speed; blue tiles return 15%. Movable apparatus follows the same rule.','Ideal vertical bounces.'),
 '08':('Every free body’s speed stays below 2.2. Larger pushes keep adding momentum, with diminishing speed gains.','Launch speed for a unit mass.'),
 '09':('Entering gray multiplies both balls’ linear and angular velocities by 0.4; leaving multiplies them by 2.5. Height does not matter.','Boundary changes only; friction and gravity omitted.'),
 '10':('Inside yellow, speeds below 0.35 get an eastward seed. Otherwise, velocity is multiplied by 1.0015 per step while below 6. Height does not matter.','Qualitative motion; per-step gain simplified.'),
 '11':('When two experiment balls separate after contact, both remaining velocities are multiplied by 1.8. Walls, floors, and apparatus do not trigger it.','Staged collision; gain applied at separation.'),
 '12':('Two free spheres swap colors once when contact begins. They must separate before another swap can occur.','Staged contacts; A and B keep their identities.'),
 '13':('Every third contact between the original red and blue balls sets both upward speeds to 4. Sustained contact counts once; other objects do not count.','Staged contacts; original counting rule.'),
 '14':('Each red launch schedules a copy 12 seconds later. Green’s velocity is replaced with the stored value, even if red is held.','Exact delay; ordinary slowing simplified.'),
 '15':('Red’s northward force starts on. A nonzero launch of any movable object pauses it for 10 seconds; another launch restarts the timer.','Extra-force effect only; other motion omitted.')
}


def catalog():
    names,_=paper_scene_names();laws,_=paper_scene_laws()
    return {id:dict(id=id,name=names[id],law=laws[id],plain=PLAIN[id][0],plain_zh=PLAIN[id][1],explanation=EXPLAIN[id][0],model_note=EXPLAIN[id][1],**entry) for id,entry in CATALOG.items()}


if __name__=='__main__':
    site=Path(__file__).resolve().parents[1]
    (site/'data/oracles.js').write_text('window.ORACLE_CATALOG = '+json.dumps(catalog(),ensure_ascii=False)+';\n')
    (site/'downloads/oracle-captions-zh.txt').write_text('\n'.join(f'{id} {entry["name"]}\n{entry["plain_zh"]}\n' for id,entry in catalog().items()),encoding='utf-8')
