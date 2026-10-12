"""Export standalone, anonymous publication figures and the sharing image."""
from pathlib import Path
import json
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import MultipleLocator
from PIL import Image, ImageDraw, ImageFont
import numpy as np

SITE=Path(__file__).resolve().parents[1]
DATA=json.loads((SITE/'data/paper.js').read_text().removeprefix('window.LONGCHANG = ').rstrip(';\n'))
FONTS=SITE/'assets/fonts'
for path in FONTS.glob('type-*'):
    font_manager.fontManager.addfont(str(path))
INK='#203c43'; MUTED='#65797c'; TEAL='#347c79'; BLUE='#688eb3'; SAGE='#aac8b9'; GRID='#e4ece8'
plt.rcParams.update({'font.family':'DM Sans','font.size':10,'text.color':INK,'axes.labelcolor':MUTED,
                     'xtick.color':MUTED,'ytick.color':INK,'axes.spines.top':False,
                     'axes.spines.right':False,'axes.spines.left':False,'axes.spines.bottom':False,
                     'svg.fonttype':'path','figure.facecolor':'white','savefig.facecolor':'white'})


def save(fig,name):
    for ext in ['svg','png']:
        fig.savefig(SITE/f'downloads/{name}.{ext}',dpi=200,metadata={'Creator':'LongChang — Anonymous Authors'} if ext=='svg' else None)
    plt.close(fig)


def main():
    models=DATA['models']
    fig,axes=plt.subplots(1,3,figsize=(13.2,7.4),sharey=True)
    fig.subplots_adjust(left=.18,right=.955,bottom=.15,top=.80,wspace=.17)
    fig.text(.045,.935,'Correct laws and supporting evidence do not always coincide.',fontfamily='Newsreader',fontsize=24)
    fig.text(.045,.875,'LongChang  /  12 models · 14 altered scenes · 3 runs per scene · up to 100 turns',fontsize=10,color=MUTED)
    y=np.arange(len(models))
    for ax,key,title,color in zip(axes,['D','C','S'],['Discovery  ·  C and S','Law correctness  ·  C','Evidence support  ·  S'],[TEAL,BLUE,SAGE]):
        values=[m[key] for m in models]
        ax.axhspan(-.4,.4,color='#edf5f0',zorder=0)
        ax.barh(y,values,height=.48,color=color,zorder=3)
        for i,value in enumerate(values):
            if value==0: ax.scatter(0,i,s=10,color='#b2c5bc',zorder=4)
            ax.text(value+1.8 if value<90 else value-2,i,f'{value:.1f}',ha='left' if value<90 else 'right',va='center',fontsize=9,color=INK)
        ax.set(xlim=(0,107),ylim=(len(models)-.4,-.8),yticks=y,yticklabels=[m['name'] for m in models])
        ax.set_xticks([0,25,50,75,100])
        ax.grid(axis='x',color=GRID,linewidth=.65,zorder=0)
        ax.tick_params(axis='both',length=0,pad=8,labelsize=9)
        ax.set_title(title,loc='left',fontweight='medium',fontsize=12,pad=16)
        ax.set_xlabel('Passing runs (%)',labelpad=14,fontsize=9)
    fig.text(.045,.055,'Judge: GPT-6.1-Sol. Each rate uses 42 altered-scene explorations per model. The normal control is excluded.',fontsize=9,color=MUTED)
    save(fig,'model-comparison')

    fig,axes=plt.subplots(1,3,figsize=(12.8,4.7))
    fig.subplots_adjust(left=.06,right=.965,bottom=.26,top=.70,wspace=.32)
    fig.text(.045,.92,'What helps an explorer discover?',fontfamily='Newsreader',fontsize=27)
    fig.text(.045,.85,'Controlled comparisons  /  GPT-6-Astra  /  Discovery rate (%)',color=MUTED,fontsize=10)
    groups=[('Task guidance',[DATA['controlled'][0],DATA['controlled'][1]],['Free','Guided']),
            ('Exploration budget',[DATA['controlled'][2],DATA['controlled'][3]],['100 turns','500 turns']),
            ('Apparatus access',[DATA['controlled'][5],DATA['controlled'][4]],['Disabled','Enabled'])]
    for ax,(title,rows,labels) in zip(axes,groups):
        vals=[r['D'] for r in rows]
        ax.bar([0,1],vals,width=.5,color=[SAGE,TEAL],zorder=3)
        for i,v in enumerate(vals):ax.text(i,v+1.3,f'{v:.1f}%',ha='center',fontsize=13,color=INK)
        ax.set(ylim=(0,40),xticks=[0,1],xticklabels=labels,yticks=[0,10,20,30,40])
        ax.tick_params(length=0,pad=9)
        ax.grid(axis='y',color=GRID,zorder=0,linewidth=.7)
        ax.set_title(title,loc='left',fontsize=13,pad=22)
    fig.text(.045,.13,'Guidance and apparatus: 100-turn main baseline. Budget comparison: matched runs without context compaction.',fontsize=9,color=MUTED)
    fig.text(.045,.075,'The two 100-turn baselines are distinct experimental conditions. All bars use the same 0–40% scale.',fontsize=9,color=MUTED)
    save(fig,'controlled-comparisons')

    fig,ax=plt.subplots(figsize=(11.5,4.8))
    fig.subplots_adjust(left=.065,right=.97,bottom=.24,top=.71)
    fig.text(.045,.92,'New conditions remain unresolved.',fontfamily='Newsreader',fontsize=27)
    fig.text(.045,.85,'Scene evolution  /  GPT-6-Astra  /  3 explorations per condition',fontsize=10,color=MUTED)
    rows=DATA['evolution'];x=np.arange(len(rows))
    ax.bar(x-.16,[r['D'] for r in rows],width=.28,color=TEAL,label='Discovery',zorder=3)
    ax.bar(x+.16,[r['S'] for r in rows],width=.28,color=SAGE,label='Evidence support',zorder=3)
    for i,r in enumerate(rows):
        ax.text(i-.16,r['D']+3,f"{r['D']:.1f}",ha='center',fontsize=10)
        ax.text(i+.16,r['S']-10,f"{r['S']:.0f}",ha='center',fontsize=9)
    ax.set(ylim=(0,115),xticks=x,xticklabels=[r['name'] for r in rows],yticks=[0,25,50,75,100],ylabel='Passing runs (%)')
    ax.tick_params(length=0,pad=9);ax.grid(axis='y',color=GRID,zorder=0)
    ax.legend(loc='upper right',bbox_to_anchor=(1,1.2),ncol=2,frameon=False,fontsize=10)
    fig.text(.045,.10,'Source-scene runs belong to the scene-evolution experiment and are separate from the main model comparison.',fontsize=9,color=MUTED)
    fig.text(.045,.045,'Law correctness equals discovery in these five conditions; evidence support is 100% throughout.',fontsize=9,color=MUTED)
    save(fig,'scene-evolution')

    # Sharing card is generated from the actual glass-room artwork.
    im=Image.new('RGB',(1200,630),'#f7f9f8');draw=ImageDraw.Draw(im)
    sans=lambda size:ImageFont.truetype(str(FONTS/'type-0.ttf'),size)
    serif=lambda size:ImageFont.truetype(str(FONTS/'type-6.ttf'),size)
    italic=lambda size:ImageFont.truetype(str(FONTS/'type-4.ttf'),size)
    draw.text((65,52),'LongChang.',font=sans(26),fill=INK)
    draw.text((65,142),'A world to explore.',font=serif(57),fill=INK)
    draw.text((65,210),'Laws to discover.',font=italic(60),fill=TEAL)
    draw.text((65,325),'Can LLMs Uncover Hidden Physical Laws',font=sans(18),fill=MUTED)
    draw.text((65,357),'through Free Exploration?',font=sans(18),fill=MUTED)
    draw.text((65,425),'15 worlds  ·  12 language models',font=sans(18),fill=INK)
    draw.text((65,550),'Anonymous research project',font=sans(15),fill=MUTED)
    art=Image.open(SITE/'assets/images/glass-world.webp').convert('RGBA');art.thumbnail((560,535))
    im.paste(art,(632,49),art)
    draw.line((65,513,1135,513),fill='#dbe4e3',width=1)
    im.save(SITE/'assets/images/social-card.png',optimize=True)
    print('Exported three figures in SVG and PNG, plus the sharing card.')


if __name__=='__main__':main()
