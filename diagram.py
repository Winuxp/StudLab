"""Dynamic three-zone stud section, detached details, edit and error overlays."""
from html import escape
from math import isfinite
from geometry import geometry_issues


def assembly_svg(thread,stud,parts,washer,nut,lower_thread=None,active=(),issues=None):
    lower=lower_thread or thread
    issues=geometry_issues(thread,lower,stud,parts,washer,nut) if issues is None else issues
    bad={z for issue in issues for z in issue['zones']};active=set(active)
    def safe(v,default=1.):
        try:v=float(v)
        except (TypeError,ValueError):return default
        return v if isfinite(v) and v>0 else default
    ss=[dict(s,L_mm=safe(s['L_mm']),diameter_mm=safe(s['diameter_mm'])) for s in stud]
    pp=[dict(p,L_mm=safe(p['L_mm']),hole_mm=safe(p['hole_mm']),effective_OD_mm=safe(p['effective_OD_mm'])) for p in parts]
    w={k:safe(v) for k,v in washer.items()};n={k:safe(v) for k,v in nut.items()}
    total_s=sum(s['L_mm'] for s in ss);total_p=sum(p['L_mm'] for p in pp)+w['thickness_mm']
    sy=300/max(total_s,total_p,1);sx=min(6,180/max([p['effective_OD_mm'] for p in pp]+[w['outer_mm'],n['bearing_outer_mm'],thread['d_mm'],lower['d_mm']]+[s['diameter_mm'] for s in ss]))
    cx=310;top=190;bottom=top+total_p*sy
    height=620+max(1,len(issues))*20
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 {height}" role="img" aria-label="Three-zone stud, two joint parts, detached nut and washer, geometry diagnostics"><rect x="1" y="1" width="898" height="{height-2}" rx="12" fill="#f8fafc" stroke="#cbd5e1"/><g font-family="Arial, sans-serif">'
    def text(x,y,label,size=13,color='#334155',anchor='start'):
        return f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(str(label))}</text>'
    def color(zone,normal):return '#dc2626' if zone in bad else '#d97706' if zone in active else normal
    def rect(x,y,width,h,fill,stroke,zone=None):
        stroke=color(zone,stroke);weight=3 if zone in bad or zone in active else 1.3
        return f'<rect data-zone="{zone or ""}" x="{x:.4f}" y="{y:.4f}" width="{max(.2,width):.4f}" height="{max(.2,h):.4f}" fill="{fill}" stroke="{stroke}" stroke-width="{weight}"/>'
    def female(center,y,height,hole,outer,zone,tint):
        # Split female thread section: a visible white bore and inward zigzag flanks.
        out='';half=outer/2;gap=hole/2
        for sign in (-1,1):
            x=center-half if sign<0 else center+gap
            out+=rect(x,y,max(3,half-gap),height,tint,'#475569',zone)
            edge=center+sign*gap
            steps=max(2,min(20,int(height/7)))
            points=[]
            for j in range(steps*2+1):
                px=edge+sign*(3 if j%2 else 0);py=y+height*j/(steps*2)
                points.append(f'{px:.3f},{py:.3f}')
            out+=f'<polyline points="{" ".join(points)}" fill="none" stroke="{color(zone,"#7c3aed" if zone=="Anchor" else "#1d4ed8")}" stroke-width="1.5"/>'
        return out
    svg+=text(22,28,'StudLab · geometry monitor',19)
    svg+=text(22,50,'S1 upper thread · S2 plain body · S3 lower thread',12)
    svg+=text(22,70,'Orange = last edited element · Red = incoherent geometry',12,'#92400e')
    # Detached nut/washer at upper right; not additional parts in the load path.
    svg+=rect(565,48,313,170,'white','#cbd5e1')
    svg+=text(580,69,'Detached details',14)
    detail_scale=64/max(w['outer_mm'],n['bearing_outer_mm'],thread['d_mm'])
    detail_h=min(43,max(12,n['height_mm']*detail_scale))
    svg+=female(620,87,detail_h,thread['d_mm']*detail_scale,max(thread['d_mm']*detail_scale+6,n['bearing_outer_mm']*detail_scale),'Nut','#cbd5e1')
    svg+=text(666,94,'Nut · internal thread',12,color('Nut','#475569'))
    svg+=text(666,111,thread.get('name','Upper thread'),12,'#1d4ed8')
    svg+=text(666,128,f"h {n['height_mm']:.3f} mm",11)
    wd=w['outer_mm']*detail_scale;wid=w['inner_mm']*detail_scale
    for sign in (-1,1):
        x=620-wd/2 if sign<0 else 620+wid/2
        svg+=rect(x,153,max(2,(wd-wid)/2),max(2,min(13,w['thickness_mm']*detail_scale)),'#fde68a','#b45309','Washer')
    ri=min(14,14*w['inner_mm']/w['outer_mm'])
    svg+=f'<circle cx="620" cy="194" r="14" fill="#fde68a" stroke="{color("Washer","#b45309")}"/><circle cx="620" cy="194" r="{ri:.3f}" fill="white" stroke="{color("Washer","#b45309")}"/>'
    svg+=text(666,160,'Washer',12,color('Washer','#92400e'))
    svg+=text(666,178,f"ID {w['inner_mm']:.3f} / OD {w['outer_mm']:.3f}",11)
    svg+=text(666,196,f"t {w['thickness_mm']:.3f} mm",11)
    # Main nut and washer. Nut remains above the washer.
    nh=min(65,max(30,n['height_mm']*sy));width=thread['d_mm']*sx
    svg+=female(cx,top-nh,nh,width+4,max(n['bearing_outer_mm']*sx,width+16),'Nut','#cbd5e1')
    svg+=rect(cx-width/2,top-nh-10,width,nh+10,'#93c5fd','#1d4ed8','S1')
    svg+=text(24,top-nh+10,'Nut: upper internal thread',12,color('Nut','#1d4ed8'))
    svg+=text(24,top-nh+28,thread.get('name',''),12,'#1d4ed8')
    wt=w['thickness_mm']*sy;wo=w['outer_mm']*sx;wi=w['inner_mm']*sx
    for sign in (-1,1):
        x=cx-wo/2 if sign<0 else cx+wi/2
        svg+=rect(x,top,max(2,(wo-wi)/2),wt,'#fde68a','#b45309','Washer')
    svg+=text(420,top+10,f"Washer t {w['thickness_mm']:.3f}",12,color('Washer','#92400e'))
    z=w['thickness_mm']
    for i,p in enumerate(pp):
        key=f'P{i+1}';y=top+z*sy;h=p['L_mm']*sy;do=p['effective_OD_mm']*sx;di=p['hole_mm']*sx
        for sign in (-1,1):
            x=cx-do/2 if sign<0 else cx+di/2
            svg+=rect(x,y,max(2,(do-di)/2),h,('#dbeafe','#ccfbf1')[i],'#64748b',key)
        yy=y+h/2
        svg+=text(540,yy,f"{key} · L {p['L_mm']:.3f} mm",14,color(key,'#334155'))
        svg+=text(540,yy+21,f"Clearance hole Ø{p['hole_mm']:.3f}",12,color(key,'#475569'))
        svg+=text(540,yy+40,f"Deff {p['effective_OD_mm']:.3f} mm",12)
        svg+=f'<path d="M{cx+do/2+4:.3f} {yy:.3f}H530" stroke="{color(key,"#94a3b8")}"/>'
        z+=p['L_mm']
    z=0
    for i,s in enumerate(ss):
        key=f'S{i+1}';y=top+z*sy;h=s['L_mm']*sy
        d=thread['d_mm'] if i==0 else lower['d_mm'] if i==2 else s['diameter_mm']
        width=d*sx;tint=('#60a5fa','#93c5fd','#c4b5fd')[i];edge=('#1d4ed8','#2563eb','#7c3aed')[i]
        svg+=rect(cx-width/2,y,width,h,tint,edge,key)
        if i!=1:
            yy=y+3
            while yy<y+h-2:
                svg+=f'<path d="M{cx-width/2:.3f} {yy:.3f}l7 3M{cx+width/2:.3f} {yy:.3f}l-7 3" stroke="{edge}"/>'
                yy+=7
        yy=y+h/2
        label=('Upper external thread','Plain body','Lower external thread')[i]
        svg+=text(24,yy,f'{key} · {label}',12,color(key,edge))
        svg+=text(24,yy+18,f"L {s['L_mm']:.3f} · Ø {d:.3f} mm",12,color(key,edge))
        if i!=1:svg+=text(24,yy+35,(thread if i==0 else lower).get('name',''),11,edge)
        svg+=f'<path d="M205 {yy:.3f}H{cx-width/2-4:.3f}" stroke="{color(key,edge)}"/>'
        z+=s['L_mm']
    # Tapped bottom anchor shown separately from P2; real engagement compliance excluded.
    d=lower['d_mm']*sx
    svg+=female(cx,bottom+8,30,d+4,max(d+60,150),'Anchor','#ede9fe')
    svg+=rect(cx-d/2,bottom+8,d,30,'#c4b5fd','#7c3aed','Anchor')
    svg+=text(540,bottom+27,'Anchor · lower tapped hole',12,color('Anchor','#7c3aed'))
    svg+=text(540,bottom+46,lower.get('name',''),12,'#7c3aed')
    svg+=f'<path d="M{cx} {top-nh-20:.3f}V{bottom+48:.3f}" stroke="#64748b" stroke-dasharray="4 5" stroke-width=".8"/>'
    if abs(total_s-total_p)>1e-6:
        for length in (total_s,total_p):
            yy=top+length*sy
            svg+=f'<path d="M190 {yy:.3f}H475" stroke="#dc2626" stroke-width="2" stroke-dasharray="5 4"/>'
        svg+=text(480,top+min(total_s,total_p)*sy-8,f'ΔL {total_s-total_p:+.3f} mm',12,'#dc2626')
    svg+=text(22,564,f'Stud ΣL {total_s:.3f} / joint + washer {total_p:.3f} mm',13)
    svg+=text(22,584,'Blue: upper external / nut internal · Purple: lower external / anchor internal',12)
    svg+=text(22,602,'Deff is a compression-model diameter. Nut / anchor engagement is schematic, excluded from active lengths.',10,'#64748b')
    if issues:
        for i,issue in enumerate(issues):svg+=text(22,626+i*20,'⚠ '+issue['message'],12,'#dc2626')
    else:svg+=text(22,626,'Geometry consistent',13,'#15803d')
    return svg+'</g></svg>'
