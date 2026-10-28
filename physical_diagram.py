"""Physical boundaries, before/after mating ends and focused editor targets."""
from html import escape
from physical import analyse


def svg(model,upper,lower,geometry=None):
    g=geometry or analyse(model,upper,lower)
    if 'stud' not in g:return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 180"><text x="20" y="40">Complete positive geometry values to restore the drawing.</text></svg>'
    top=max(g['stud_tip'],g['nut_top'],1);k=420/top;cx=245;yb=505
    def y(z):return yb-z*k
    bad={z for issue in g['issues'] for z in issue['zones']}
    maxd=max([p['OD'] for p in model['parts']]+[s['d'] for s in model['stud']]+[model['washer']['OD'],upper['d_mm'],lower['d_mm']]);sx=min(6,180/maxd)
    out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 660" role="img" aria-label="Physical stud assembly numbered from bottom, mating thread boundaries and interval decomposition"><style>.focused rect,.focused path,.focused polyline,.focused line{stroke:#d97706!important;stroke-width:3!important}.focused text{fill:#b45309!important}.geometry-error rect,.geometry-error path,.geometry-error polyline{stroke:#dc2626!important}.geometry-error text{fill:#dc2626!important}</style><rect width="800" height="660" rx="12" fill="#f8fafc" stroke="#cbd5e1"/><g font-family="Arial,sans-serif">']
    def txt(x,yy,s,size=12,color='#334155'):return f'<text x="{x:.3f}" y="{yy:.3f}" font-size="{size}" fill="{color}">{escape(str(s))}</text>'
    def group(key,body):return f'<g data-zone="{key}" class="{"geometry-error" if key in bad else ""}">{body}</g>'
    def rect(x,yy,w,h,fill,stroke):return f'<rect x="{x:.3f}" y="{yy:.3f}" width="{max(w,.2):.3f}" height="{max(h,.2):.3f}" fill="{fill}" stroke="{stroke}"/>'
    def female(key,z0,z1,d,od,fill,col):
      body='';di=d*sx;do=od*sx;yy=y(z1);h=(z1-z0)*k
      for sign in (-1,1):
        x=cx-do/2 if sign<0 else cx+di/2;body+=rect(x,yy,(do-di)/2,h,fill,col)
        edge=cx+sign*di/2;points=[];steps=max(2,min(24,int(h/7)))
        for j in range(steps*2+1):points.append(f'{edge+sign*(3 if j%2 else 0):.2f},{yy+h*j/(steps*2):.2f}')
        body+=f'<polyline points="{" ".join(points)}" fill="none" stroke="{col}"/>'
      return group(key,body)
    out.append(txt(20,26,'Physical lengths · bottom-up origin z = 0',17))
    out.append(txt(20,47,'Orange: focused field · red: invalid geometry · C: intersection intervals',11))
    # Anchor and physical female length start exactly at zero, same as stud tip.
    out.append(female('Anchor',0,g['anchor_top'],lower['d_mm']+.5,max(3*lower['d_mm'],maxd), '#ede9fe','#7c3aed'))
    for p in g['parts']:
      body='';do=p['OD']*sx;di=p['hole']*sx
      for sign in (-1,1):body+=rect(cx-do/2 if sign<0 else cx+di/2,y(p['z1']),(do-di)/2,p['L']*k,'#dbeafe' if p['id']=='P1' else '#ccfbf1','#64748b')
      body+=txt(515,y((p['z0']+p['z1'])/2),f"{p['id']} L {p['L']:.3f}")
      body+=txt(515,y((p['z0']+p['z1'])/2)+17,f"hole {p['hole']:.3f} / Deff {p['OD']:.3f}",11)
      out.append(group(p['id'],body))
    w=model['washer'];n=model['nut'];wi=w['ID']*sx;wo=w['OD']*sx
    body=''
    for sign in (-1,1):body+=rect(cx-wo/2 if sign<0 else cx+wi/2,y(g['nut_bottom']),(wo-wi)/2,w['t']*k,'#fde68a','#b45309')
    out.append(group('Washer',body))
    out.append(female('Nut',g['nut_bottom'],g['nut_top'],upper['d_mm']+.5,max(n['OD'],upper['d_mm']+1),'#cbd5e1','#2563eb'))
    for s in g['stud']:
      t=lower if s['kind']=='Lower' else upper;d=t['d_mm'] if s['kind']!='Plain' else s['d'];width=d*sx
      fill='#c4b5fd' if s['kind']=='Lower' else '#60a5fa' if s['kind']=='Upper' else '#93c5fd';col='#7c3aed' if s['kind']=='Lower' else '#1d4ed8'
      body=rect(cx-width/2,y(s['z1']),width,s['L']*k,fill,col)
      if s['kind']!='Plain':
        yy=y(s['z1'])+3
        while yy<y(s['z0'])-2:
          body+=f'<path d="M{cx-width/2:.2f} {yy:.2f}l6 3M{cx+width/2:.2f} {yy:.2f}l-6 3" stroke="{col}"/>';yy+=7
      yy=y((s['z0']+s['z1'])/2)
      body+=txt(18,yy,s['id']+' '+s['kind'],12,col)+txt(18,yy+17,f"L {s['L']:.3f} / Ø {d:.3f}",11,col)
      body+=f'<path d="M135 {yy:.2f}H{cx-width/2-4:.2f}" stroke="{col}"/>'
      out.append(group(s['id'],body))
    # Every end of either member produces a new interval. Independent physical ends stay visible.
    for i,s in enumerate(g['segments']):
      mid=(s['z0']+s['z1'])/2;yy=y(mid);h=s['L']*k
      fill='#ede9fe' if s['state']=='engaged' else '#d1fae5' if s['state']=='free loaded' else '#e2e8f0'
      out.append(f'<g data-zone="{s["stud"]}" data-related="{s["opposite"]}" class="interval">'+rect(402,y(s['z1']),15,h,fill,'#94a3b8')+txt(423,yy+3,f"C{i+1} · {s['L']:.3f}",9)+'</g>')
    for key,z,label,col in [('Anchor',g['anchor_top'],'Tap end','#7c3aed'),(g['stud'][0]['id'],g['stud'][0]['z1'],'Male lower end','#7c3aed'),('Nut',g['nut_bottom'],'Nut start','#2563eb'),('Nut',g['nut_top'],'Nut end','#2563eb'),(g['stud'][-1]['id'],g['stud'][-1]['z0'],'Upper thread start','#2563eb')]:
      yy=y(z)
      out.append(group(key,f'<path d="M{cx-75} {yy:.3f}H{cx+75}" stroke="{col}" stroke-dasharray="4 3"/>'))
    out.append(txt(18,528,f"z = 0 · common lower male/female start · engagement {g['lower_engagement']:.3f} mm",11))
    out.append(txt(18,547,f"Nut engagement {g['upper_engagement']:.3f} mm · stud tip z {g['stud_tip']:.3f} / nut top z {g['nut_top']:.3f}",11))
    out.append(txt(18,566,'Drawn length ≠ elastic equivalent length. C intervals are geometric, not extra springs.',11))
    # Detached details at top right with immediate focus hooks.
    out.append(rect(520,60,260,105,'white','#cbd5e1'))
    out.append(group('Nut',rect(537,88,22,25,'#cbd5e1','#2563eb')+rect(578,88,22,25,'#cbd5e1','#2563eb')+txt(615,99,'Nut / upper tap',11)+txt(615,115,f"h {n['h']:.3f}",11)))
    out.append(group('Washer',rect(537,136,22,7,'#fde68a','#b45309')+rect(578,136,22,7,'#fde68a','#b45309')+txt(615,141,f"Washer t {w['t']:.3f}",11)))
    if g['issues']:
      for i,issue in enumerate(g['issues'][:4]):out.append(txt(18,587+i*17,issue['message'][:112],10,'#dc2626'))
    else:out.append(txt(18,592,'Geometry consistent · lower/upper excess lengths may be intentional.',12,'#15803d'))
    out.append('</g></svg>');return ''.join(out)
