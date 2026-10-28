"""Elastic three-zone stud / two-annulus joint model. mm, N, MPa, N.mm internally.
Not a complete VDI 2230 implementation; see README for load-path assumptions.
"""
from math import pi, atan, tan, cos, sqrt, isfinite, degrees


def number(value, label, minimum=None, strict=False):
    try:v=float(value)
    except (ValueError,TypeError,OverflowError):raise ValueError(f'{label}: enter a number.') from None
    if not isfinite(v):raise ValueError(f'{label}: value must be finite.')
    if minimum is not None and (v<=minimum if strict else v<minimum):
        raise ValueError(f'{label}: must be {">" if strict else "≥"} {minimum:g}.')
    return v


def thread_geometry(row):
    d=number(row['d_mm'],'Thread d',0,True);p=number(row['pitch_mm'],'Pitch',0,True)
    d2=number(row.get('d2_mm',d-.6495190528*p),'Pitch diameter',0,True)
    d3=number(row.get('d3_mm',d-1.226869322*p),'Root diameter',0,True)
    area=number(row.get('As_mm2',pi/4*((d2+d3)/2)**2),'Tensile stress area',0,True)
    if not d>d2>d3>0:raise ValueError('Thread geometry must satisfy d > d2 > d3 > 0.')
    return dict(d_mm=d,pitch_mm=p,d2_mm=d2,d3_mm=d3,As_mm2=area)


def default_inputs(thread, lower_thread=None):
    d=thread['d_mm'];dl=(lower_thread or thread)['d_mm'];dh=max(d,dl)+.5
    return dict(
        stud=[dict(ID=f'S{i+1}',Profile='Threaded' if i in (0,2) else 'Plain',
                   L_mm=v,diameter_mm=dl if i==2 else d,E_GPa=210.,nu=.3,Rp_MPa=900.)
              for i,v in enumerate((8.,30.,14.))],
        parts=[dict(ID=f'P{i+1}',L_mm=25.,hole_mm=dh,effective_OD_mm=3*max(d,dl),
                    E_GPa=210.,p_allow_MPa=300.) for i in range(2)],
        washer=dict(thickness_mm=2.,inner_mm=d+.5,outer_mm=2*d,E_GPa=210.,p_allow_MPa=300.),
        nut=dict(height_mm=.8*d,bearing_inner_mm=d+.5,bearing_outer_mm=1.6*d,p_allow_MPa=300.))


def calculate(thread,stud,parts,washer,nut,target_n,snug_nm,mu_thread,mu_bearing,closure_um=0,lower_thread=None,_variable=False):
    t=thread_geometry(thread)
    lower=thread_geometry(lower_thread or thread)
    if not _variable and (len(stud)!=3 or len(parts)!=2):raise ValueError('Exactly three stud zones and two joint parts are required.')
    if not _variable and [r.get('Profile') for r in stud]!=['Threaded','Plain','Threaded']:
        raise ValueError('Stud profiles must be upper thread / plain body / lower thread.')
    f=number(target_n,'Target tension',0,True)
    snug=number(snug_nm,'Snug torque',0)
    mg=number(mu_thread,'Thread friction',0);mk=number(mu_bearing,'Bearing friction',0)
    closure=number(closure_um,'Additional closure',0)/1000
    half_angle=pi/6
    lead=atan(t['pitch_mm']/(pi*t['d2_mm']))
    friction_angle=atan(mg/cos(half_angle))
    if lead+friction_angle>=pi/2:raise ValueError('Thread friction/pitch is outside the screw model domain.')
    w={k:number(washer[k],'Washer '+k,0,True) for k in ('thickness_mm','inner_mm','outer_mm','E_GPa','p_allow_MPa')}
    n={k:number(nut[k],'Nut '+k,0,True) for k in ('height_mm','bearing_inner_mm','bearing_outer_mm','p_allow_MPa')}
    wi,wo=w['inner_mm'],w['outer_mm'];bi,bo=n['bearing_inner_mm'],n['bearing_outer_mm']
    if not t['d_mm']<wi<wo:raise ValueError('Washer geometry must satisfy thread d < ID < OD.')
    if not wi<=bi<bo<=wo:raise ValueError('Nut bearing annulus must lie on the washer: washer ID ≤ bearing ID < bearing OD ≤ washer OD.')
    # Uniform bearing pressure, not the uniform-wear arithmetic diameter.
    db=2/3*(bo**3-bi**3)/(bo**2-bi**2)
    c_thread=t['d2_mm']/2*tan(lead+friction_angle)
    c_bearing=mk*db/2
    c_total=c_thread+c_bearing
    f0=snug*1000/c_total
    if f0>f*(1+1e-12):raise ValueError(f'Snug torque already gives {f0:.0f} N, above the target. Reduce snug torque or increase target.')
    mt=f*c_thread;mt0=f0*c_thread
    srows=[];cs=ct=0.;z=0.
    for i,row in enumerate(stud):
        label=f'S{i+1}'
        length=number(row['L_mm'],label+' length',0,True)
        e=number(row['E_GPa'],label+' E',0,True)*1000
        nu=number(row['nu'],label+' nu')
        if not -1<nu<.5:raise ValueError(label+': Poisson ratio must be between −1 and 0.5.')
        rp=number(row['Rp_MPa'],label+' yield strength',0,True)
        if row['Profile'] not in ('Threaded','Plain'):raise ValueError(label+': unknown profile.')
        threaded=row['Profile']=='Threaded'
        local_thread=lower if row.get('thread_end')=='Lower' or (not _variable and i==2) else t
        d=local_thread['d3_mm'] if threaded else number(row['diameter_mm'],label+' diameter',0,True)
        nominal=local_thread['d_mm'] if threaded else d
        a=pi*d*d/4;ast=local_thread['As_mm2'] if threaded else a
        j=pi*d**4/32;g=e/(2*(1+nu))
        compliance=length/(e*a);torsion=length/(g*j)
        sigma=f/ast;tau=mt*d/(2*j);vm=sqrt(sigma**2+3*tau**2)
        srows.append(dict(ID=label,profile=row['Profile'],length_mm=length,diameter_mm=nominal,
                          root_mm=d,area_compliance_mm2=a,stress_area_mm2=ast,
                          compliance_mm_n=compliance,stiffness_n_mm=1/compliance,
                          torsion_compliance_rad_nmm=torsion,J_mm4=j,G_MPa=g,
                          elongation_mm=f*compliance,increment_mm=(f-f0)*compliance,
                          twist_deg=degrees(mt*torsion),increment_twist_deg=degrees((mt-mt0)*torsion),
                          sigma_MPa=sigma,tau_MPa=tau,vm_MPa=vm,yield_MPa=rp,
                          utilization=vm/rp,yield_factor=rp/vm,z0=z,z1=z+length))
        cs+=compliance;ct+=torsion;z+=length
    prows=[];cp=0.;zp=w['thickness_mm']
    for i,row in enumerate(parts):
        label=f'P{i+1}'
        length=number(row['L_mm'],label+' length',0,True)
        di=number(row['hole_mm'],label+' hole',0,True)
        do=number(row['effective_OD_mm'],label+' effective OD',0,True)
        e=number(row['E_GPa'],label+' E',0,True)*1000
        allow=number(row['p_allow_MPa'],label+' allowable pressure',0,True)
        if do<=di:raise ValueError(label+': effective OD must exceed hole diameter.')
        crossed=[s['diameter_mm'] for s in srows if min(s['z1'],zp+length)-max(s['z0'],zp)>1e-8]
        if not _variable and crossed and di<=max(crossed):raise ValueError(label+': hole must clear every overlapping stud segment.')
        a=pi/4*(do*do-di*di);c=length/(e*a);pressure=f/a
        prows.append(dict(ID=label,length_mm=length,hole_mm=di,effective_OD_mm=do,
                          area_mm2=a,compliance_mm_n=c,stiffness_n_mm=1/c,
                          contraction_mm=f*c,increment_mm=(f-f0)*c,
                          compression_MPa=pressure,p_allow_MPa=allow,utilization=pressure/allow))
        cp+=c;zp+=length
    if not _variable and any(s['diameter_mm']>=wi for s in srows if s['z0']<w['thickness_mm']):
        raise ValueError('Washer hole must clear the stud.')
    grip=zp
    if not _variable and abs(z-grip)>max(1e-6,grip*1e-6):
        raise ValueError(f'Load-path mismatch: stud ΣL = {z:.3f} mm; parts + washer = {grip:.3f} mm. These must match in this model.')
    if not _variable and stud[0]['Profile']!='Threaded':raise ValueError('S1 must be threaded: load enters the stud through the top nut.')
    aw=pi/4*(wo*wo-wi*wi);cw=w['thickness_mm']/(w['E_GPa']*1000*aw)
    # Actual overlap of washer lower face and top part's effective annulus.
    outer=min(wo,prows[0]['effective_OD_mm']);inner=max(wi,prows[0]['hole_mm'])
    if outer<=inner:raise ValueError('Washer has no supporting annular area on P1.')
    support=pi/4*(outer**2-inner**2)
    bearing_area=pi/4*(bo**2-bi**2)
    washer_pressure=f/aw;nut_pressure=f/bearing_area;support_pressure=f/support
    c_parts=cp+cw;c_all=cs+c_parts
    helix_angle=360*((f-f0)*c_all+closure)/t['pitch_mm']
    twist_angle=degrees((mt-mt0)*ct)
    total_angle=helix_angle+twist_angle
    limiting=min(s['yield_MPa']/sqrt((1/s['stress_area_mm2'])**2+
                      3*(c_thread*s['root_mm']/(2*s['J_mm4']))**2) for s in srows)
    elastic=f<=limiting
    pressure_ok=all(p['utilization']<=1 for p in prows) and max(washer_pressure,nut_pressure,support_pressure)<=w['p_allow_MPa'] and nut_pressure<=n['p_allow_MPa'] and support_pressure<=prows[0]['p_allow_MPa']
    return dict(thread=t,lower_thread=lower,stud=srows,parts=prows,washer=w,nut=n,
                target_n=f,snug_preload_n=f0,snug_torque_nm=snug,mu_thread=mg,mu_bearing=mk,
                bearing_mean_mm=db,bearing_area_mm2=bearing_area,
                thread_torque_nm=mt/1000,bearing_torque_nm=f*c_bearing/1000,
                pitch_torque_nm=f*t['pitch_mm']/(2*pi)/1000,
                thread_friction_torque_nm=(mt-f*t['pitch_mm']/(2*pi))/1000,
                final_torque_nm=f*c_total/1000,angle_deg=total_angle,
                helix_angle_deg=helix_angle,twist_increment_deg=twist_angle,
                stud_twist_deg=degrees(mt*ct),torsion_compliance_rad_nmm=ct,
                stud_compliance_mm_n=cs,parts_compliance_mm_n=c_parts,
                joint_compliance_mm_n=c_all,stud_stiffness_n_mm=1/cs,
                parts_stiffness_n_mm=1/c_parts,joint_stiffness_n_mm=1/c_all,
                ideal_load_fraction=c_parts/c_all,
                stud_elongation_mm=f*cs,parts_contraction_mm=f*c_parts,
                washer_contraction_mm=f*cw,washer_compliance_mm_n=cw,
                washer_pressure_MPa=washer_pressure,nut_pressure_MPa=nut_pressure,
                washer_support_pressure_MPa=support_pressure,
                additional_closure_mm=closure,grip_mm=grip,
                elastic_limit_n=limiting,elastic_ok=elastic,pressure_ok=pressure_ok,
                instruction_valid=elastic and pressure_ok,
                max_vm_MPa=max(s['vm_MPa'] for s in srows),
                min_yield_factor=min(s['yield_factor'] for s in srows))
