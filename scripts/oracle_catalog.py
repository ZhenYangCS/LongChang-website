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


def catalog():
    names,_=paper_scene_names();laws,_=paper_scene_laws()
    return {id:dict(id=id,name=names[id],law=laws[id],**entry) for id,entry in CATALOG.items()}


if __name__=='__main__':
    site=Path(__file__).resolve().parents[1]
    (site/'data/oracles.js').write_text('window.ORACLE_CATALOG = '+json.dumps(catalog(),ensure_ascii=False)+';\n')
