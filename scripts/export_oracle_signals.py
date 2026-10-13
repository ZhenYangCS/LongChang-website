"""Standalone measured-signal figures for the newly scripted oracle tests."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

SITE=Path(__file__).resolve().parents[1]


def main():
    font_manager.fontManager.addfont(str(SITE/'assets/fonts/DejaVuSans.ttf'))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'path',
        'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,
        'axes.labelcolor':'#647f82','text.color':'#29474c','xtick.color':'#789294',
        'ytick.color':'#789294','figure.facecolor':'#f8faf8','axes.facecolor':'#f8faf8'})
    out=SITE/'downloads/oracle-signals';out.mkdir(exist_ok=True)
    entries=json.loads((SITE/'data/physics.js').read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    for data in entries:
        id=data['id'];oracle,plot,spec=data['oracle'],data['plot'],data
        fig,ax=plt.subplots(figsize=(9.5,4.5));fig.subplots_adjust(left=.11,right=.965,top=.73,bottom=.24)
        fig.text(.07,.91,f"{id} / {oracle['name']}",fontsize=19)
        fig.text(.07,.83,oracle['formula'],fontsize=12,color='#467b70')
        if id=='12':
            times=np.asarray(plot['times'])
            for k,values in enumerate(plot['series']):
                for j in range(len(times)-1):
                    ax.broken_barh([(times[j],times[j+1]-times[j])],(k-.25,.5),facecolors='#ca876e' if values[j]>.5 else '#779fc7',edgecolors='none')
            ax.set_yticks([0,1],['Object A','Object B']);ax.set_ylim(-.65,1.65)
        else:
            for values,label,color in zip(plot['series'],plot['labels'],plot['colors']):
                ax.plot(plot['times'],values,label=label,color=color,lw=2,ls='--' if 'reference' in label else '-')
            ax.legend(loc='best',frameon=False,fontsize=9)
            ax.set_ylabel(f"{oracle['measure']} ({oracle['unit']})")
            if min(min(s) for s in plot['series'])>=0:ax.set_ylim(bottom=0)
        if id in ['05','08']:
            value=2.5 if id=='05' else 2.2
            ax.axhline(value,color='#87a778',lw=1,ls=':')
            ax.text(spec['simulation_duration']*.98,value,f' {value:g} threshold',ha='right',va='bottom',fontsize=8,color='#76946a')
        ax.set_xlim(0,spec['simulation_duration']);ax.set_xlabel('Simulation time (counts)')
        ax.grid(axis='y',color='#dce6e2',lw=.6);ax.set_axisbelow(True)
        ax.spines['bottom'].set_color('#ceddd7');ax.tick_params(length=0)
        fig.text(.07,.105,'Fresh scripted experiment. Curves are recorded simulation samples; they are not model-discovery results.',fontsize=8,color='#829794')
        fig.text(.07,.055,'Ordinary reference: identical geometry, masses and actions with the altered physical program disabled.',fontsize=8,color='#829794')
        for ext in ['svg','png']:
            fig.savefig(out/f'scene-{id}.{ext}',dpi=180,metadata={'Creator':'LongChang — Anonymous Authors'} if ext=='svg' else None)
        plt.close(fig)
    print('Exported all 15 measured-signal figures as SVG and PNG.')


if __name__=='__main__':main()
