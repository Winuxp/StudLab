"""Geometry diagnostics and parameter-change monitoring shared by UI and SVG."""
from math import isfinite


def geometry_issues(upper,lower,stud,parts,washer,nut):
    issues=[]
    def report(zones,message):issues.append(dict(zones=zones,message=message))
    vals=[]
    for group,rows,fields in [('S',stud,['L_mm','diameter_mm','E_GPa','nu','Rp_MPa']),
                              ('P',parts,['L_mm','hole_mm','effective_OD_mm','E_GPa','p_allow_MPa'])]:
        for i,row in enumerate(rows):
            for field in fields:
                try:v=float(row[field]);good=isfinite(v) and (v>0 if field!='nu' else -1<v<.5)
                except (TypeError,ValueError,KeyError):good=False
                if not good:report([f'{group}{i+1}'],f'{group}{i+1}: invalid {field}.')
    for name,row in [('Washer',washer),('Nut',nut)]:
        for k,value in row.items():
            try:good=isfinite(float(value)) and float(value)>0
            except (TypeError,ValueError):good=False
            if not good:report([name],f'{name}: invalid {k}.')
    if issues:return issues
    z=0;surfaces=[]
    for i,row in enumerate(stud):
        d=upper['d_mm'] if i==0 else lower['d_mm'] if i==2 else float(row['diameter_mm'])
        surfaces.append((z,z+float(row['L_mm']),d,f'S{i+1}'));z+=float(row['L_mm'])
    grip=float(washer['thickness_mm'])+sum(float(p['L_mm']) for p in parts)
    if abs(z-grip)>max(1e-6,grip*1e-6):
        report(['S1','S2','S3','P1','P2','Washer'],f'Length mismatch: stud {z:.3f} / stack + washer {grip:.3f} mm (Δ {z-grip:+.3f}).')
    wi=float(washer['inner_mm']);wo=float(washer['outer_mm'])
    if wo<=wi:report(['Washer'],'Washer OD must exceed ID.')
    if wi<=max(d for a,b,d,k in surfaces if a<float(washer['thickness_mm'])):
        report(['Washer','S1'],'Washer hole does not clear the stud.')
    bi=float(nut['bearing_inner_mm']);bo=float(nut['bearing_outer_mm'])
    if not wi<=bi<bo<=wo:
        report(['Washer','Nut'],'Nut bearing annulus must lie on the washer.')
    if float(stud[0]['L_mm'])<float(washer['thickness_mm']):
        report(['S1','Washer'],'Upper active thread ends inside the washer.')
    z=float(washer['thickness_mm'])
    for i,p in enumerate(parts):
        zone=f'P{i+1}';length=float(p['L_mm']);di=float(p['hole_mm']);do=float(p['effective_OD_mm'])
        if do<=di:report([zone],f'{zone}: effective OD must exceed hole Ø.')
        for a,b,d,key in surfaces:
            if min(b,z+length)-max(a,z)>1e-8 and di<=d:
                report([zone,key],f'{zone} hole Ø{di:.3f} interferes with {key} Ø{d:.3f}.')
        z+=length
    p=parts[0]
    if min(wo,float(p['effective_OD_mm']))<=max(wi,float(p['hole_mm'])):
        report(['Washer','P1'],'No washer/P1 supporting overlap.')
    return issues


def changed_zones(previous,current):
    """Highlight the last committed edit, including changes inside editor rows."""
    if previous is None:return [],''
    zones=[];labels=[]
    for group in ('stud','parts'):
        for i,row in enumerate(current[group]):
            old=previous[group][i] if i<len(previous[group]) else {}
            keys=[k for k,v in row.items() if old.get(k)!=v]
            if keys:
                zone=('S' if group=='stud' else 'P')+str(i+1);zones.append(zone)
                names={'L_mm':'length','diameter_mm':'body diameter','E_GPa':'Young E','nu':'Poisson ratio','Rp_MPa':'yield strength','hole_mm':'hole diameter','effective_OD_mm':'effective diameter','p_allow_MPa':'pressure limit'}
                labels.append(zone+': '+', '.join(names.get(k,k) for k in keys))
    for group,zone in [('washer','Washer'),('nut','Nut')]:
        if current[group]!=previous[group]:zones.append(zone);labels.append(zone+' parameters')
    for key,mapped in [('upper_thread',['S1','Nut']),('lower_thread',['S3','Anchor']),
                       ('mu_g',['S1','S2','S3','Nut','Anchor']),('mu_k',['Nut','Washer']),
                       ('target',['S1','S2','S3','P1','P2','Washer']),
                       ('snug',['S1','S2','S3','Nut']),('closure',['P1','P2','Washer'])]:
        if current.get(key)!=previous.get(key):zones.extend(mapped);labels.append(key.replace('_',' '))
    return list(dict.fromkeys(zones)), '; '.join(labels)
