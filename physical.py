"""Bottom-up physical geometry, intersection decomposition and equivalent springs.
Reference axial factors remain editable; torsional substitutes are independent inputs.
"""
from math import pi,sqrt,degrees,isfinite
from mechanics import calculate,thread_geometry,number


def defaults(upper,lower):
    d=upper['d_mm'];dl=lower['d_mm'];dh=max(d,dl)+.5
    return dict(
      stud=[dict(id='S1',name='Lower external thread',kind='Lower',L=14.,d=dl,E=210.,nu=.3,Rp=900.),
            dict(id='S2',name='Body',kind='Plain',L=30.,d=min(d,dl),E=210.,nu=.3,Rp=900.),
            dict(id='S3',name='Upper external thread',kind='Upper',L=30.,d=d,E=210.,nu=.3,Rp=900.)],
      parts=[dict(id='P1',name='Lower clamped part',L=25.,hole=dh,OD=3*max(d,dl),E=210.,p=300.),
             dict(id='P2',name='Upper clamped part',L=25.,hole=dh,OD=3*max(d,dl),E=210.,p=300.)],
      washer=dict(id='Washer',t=2.,ID=d+.5,OD=2*d,E=210.,p=300.),
      nut=dict(id='Nut',h=.8*d,ID=d+.5,OD=1.6*d,E=210.,p=300.,kg=.5,km=.4,Ltors=0.),
      anchor=dict(id='Anchor',L=12.,E=210.,kg=.5,km=.33,Ltors=0.))


def analyse(model,upper,lower):
    """Union of physical end coordinates. All z values measured from lower tips."""
    m=model;issues=[];warnings=[]
    def err(zones,message):issues.append(dict(zones=zones,message=message))
    for group in ('stud','parts'):
      for row in m[group]:
        fields=('L','d','E','Rp') if group=='stud' else ('L','hole','OD','E','p')
        for k in fields:
          try:number(row[k],row['id']+' '+k,0,True)
          except ValueError as exc:err([row['id']],str(exc))
        if group=='stud':
          try:
            nu=number(row['nu'],'Poisson ratio')
            if not -1<nu<.5:raise ValueError('Poisson ratio must lie between -1 and 0.5.')
          except ValueError as exc:err([row['id']],str(exc))
    for key in ('washer','nut','anchor'):
      for k,v in m[key].items():
        if k=='id':continue
        try:number(v,key+' '+k,0,k not in ('Ltors','kg','km'))
        except ValueError as exc:err([m[key]['id']],str(exc))
    if issues:return dict(issues=issues,warnings=warnings,segments=[],suggestions={})
    stud=[];z=0
    for row in m['stud']:
      row=dict(row,z0=z,z1=z+row['L']);z=row['z1'];stud.append(row)
    if len(stud)<3 or stud[0]['kind']!='Lower' or stud[-1]['kind']!='Upper' or any(s['kind']!='Plain' for s in stud[1:-1]):
      err([s['id'] for s in stud],'Keep one lower thread first, plain body segments, and one upper thread last.')
    la=m['anchor']['L'];parts=[];z=la
    for row in m['parts']:
      row=dict(row,z0=z,z1=z+row['L']);z=row['z1'];parts.append(row)
    w0=z;n0=z+m['washer']['t'];n1=n0+m['nut']['h'];end=stud[-1]['z1']
    lower_end=stud[0]['z1'];upper_start=stud[-1]['z0']
    low_overlap=max(0,min(lower_end,la));up_overlap=max(0,min(end,n1)-max(upper_start,n0))
    if not low_overlap:err(['S1','Anchor'],'No lower thread engagement.')
    if not up_overlap:err([stud[-1]['id'],'Nut'],'No upper thread / nut engagement.')
    if end<n1-1e-8:
      warnings.append(f'Nut extends {n1-end:.3f} mm above the stud tip; only the actual overlap is engaged. Thread stripping is not checked.')
    for s in stud:
      diam=lower['d_mm'] if s['kind']=='Lower' else upper['d_mm'] if s['kind']=='Upper' else s['d']
      if s['kind']=='Plain' and min(s['z1'],la)-s['z0']>1e-8 and diam>=lower['d3_mm']:
        err([s['id'],'Anchor'],'Plain body interferes with unused lower tapped thread; reduce body Ø or change thread/tap lengths.')
      if s['kind']=='Plain' and min(s['z1'],n1)-max(s['z0'],n0)>1e-8 and diam>=upper['d3_mm']:
        err([s['id'],'Nut'],'Plain body interferes with unused nut thread; reduce body Ø or move the upper thread start.')
      for p in parts:
        if min(s['z1'],p['z1'])-max(s['z0'],p['z0'])>1e-8 and diam>=p['hole']:
          err([s['id'],p['id']],f"{p['id']} clearance hole interferes with {s['id']}.")
      if min(s['z1'],n0)-max(s['z0'],w0)>1e-8 and diam>=m['washer']['ID']:
        err([s['id'],'Washer'],'Washer hole interferes with stud.')
    for p in parts:
      if p['OD']<=p['hole']:err([p['id']],'Effective OD must exceed hole diameter.')
    w=m['washer'];n=m['nut']
    if not upper['d_mm']<w['ID']<w['OD']:err(['Washer'],'Washer must satisfy upper thread d < ID < OD.')
    if not w['ID']<=n['ID']<n['OD']<=w['OD']:err(['Nut','Washer'],'Nut bearing annulus must lie on the washer.')
    if min(w['OD'],parts[-1]['OD'])<=max(w['ID'],parts[-1]['hole']):err(['Washer',parts[-1]['id']],'Washer has no support on the top part.')
    for key,t,engaged,zones in [('anchor',lower,low_overlap,[stud[0]['id'],'Anchor']),('nut',upper,up_overlap,[stud[-1]['id'],'Nut'])]:
      if m[key]['kg']*t['d_mm']>engaged+1e-8:
        err(zones,f'{key}: equivalent male length exceeds the physical engaged length. Verify factor or geometry.')
      if m[key]['Ltors']>engaged+1e-8:err(zones,f'{key}: torsional equivalent length exceeds engagement.')
    cuts={0.,la,lower_end,upper_start,end,w0,n0,n1}
    cuts.update(s[k] for s in stud for k in ('z0','z1'));cuts.update(p[k] for p in parts for k in ('z0','z1'))
    cuts=sorted(cuts);segments=[]
    for a,b in zip(cuts,cuts[1:]):
      if b-a<1e-9:continue
      mid=(a+b)/2;s=next((s for s in stud if s['z0']<=mid<s['z1']),None)
      female='Anchor' if mid<la else 'Nut' if n0<=mid<n1 else 'Washer' if w0<=mid<n0 else next((p['id'] for p in parts if p['z0']<=mid<p['z1']),'None')
      state='engaged' if s and ((female=='Anchor' and s['kind']=='Lower') or (female=='Nut' and s['kind']=='Upper')) else 'free loaded' if s and min(lower_end,la)<=mid<max(upper_start,n0) else 'unloaded / geometric'
      segments.append(dict(z0=a,z1=b,L=b-a,stud=s['id'] if s else 'None',kind=s['kind'] if s else 'None',opposite=female,state=state))
    suggestions={}
    # Canonical target: a fully threaded nut with zero protrusion. Excess protrusion
    # and lower-end overhang are allowed and are not forced to disappear.
    for s in stud:
      other=sum(q['L'] for q in stud if q['id']!=s['id'])
      value=n1-other
      if value>0:
        suggestions[f"stud.{s['id']}.L"]=dict(value=value,reason='Align stud tip with nut top; then recheck upper-thread start and all clearances.')
    for p in parts:
      value=end-(n1-n0)-la-w['t']-sum(q['L'] for q in parts if q['id']!=p['id'])
      if value>0:suggestions[f"parts.{p['id']}.L"]=dict(value=value,reason='Align nut top with stud tip; recheck all other dimensions.')
    for path,current,value in [('anchor.Anchor.L',la,end-(n1-n0)-w['t']-sum(p['L'] for p in parts)),('washer.Washer.t',w['t'],end-(n1-n0)-la-sum(p['L'] for p in parts)),('nut.Nut.h',n['h'],end-n0)]:
      if value>0:suggestions[path]=dict(value=value,reason='Align nut top and stud tip; other constraints remain to be checked.')
    # Body is the natural correction when upper thread starts too high. Minimum
    # change to put upper thread start at the nut base, preserving its length.
    if upper_start>n0:
      for s in stud[1:-1]:
        value=s['L']-(upper_start-n0)
        if value>0:suggestions[f"stud.{s['id']}.L"]=dict(value=value,reason='Bring upper thread start down to the nut bearing face; coverage still must be checked.')
    return dict(issues=issues,warnings=warnings,segments=segments,suggestions=suggestions,
                stud=stud,parts=parts,anchor_top=la,washer_bottom=w0,nut_bottom=n0,nut_top=n1,stud_tip=end,
                lower_engagement=low_overlap,upper_engagement=up_overlap,free_start=min(lower_end,la),free_end=max(upper_start,n0))


def solve(model,upper_raw,lower_raw,target,snug,mu_g,mu_k,closure=0):
    u=thread_geometry(upper_raw);l=thread_geometry(lower_raw);g=analyse(model,u,l)
    if g['issues']:raise ValueError('; '.join(i['message'] for i in g['issues']))
    free=[]
    # Old independent engine works top-down on the free grip; physical model is bottom-up.
    for s in reversed(g['stud']):
      a=max(s['z0'],g['free_start']);b=min(s['z1'],g['free_end'])
      if b<=a:continue
      free.append(dict(ID=s['id'],Profile='Plain' if s['kind']=='Plain' else 'Threaded',thread_end=s['kind'],L_mm=b-a,diameter_mm=s['d'],E_GPa=s['E'],nu=s['nu'],Rp_MPa=s['Rp']))
    p=[dict(ID=r['id'],L_mm=r['L'],hole_mm=r['hole'],effective_OD_mm=r['OD'],E_GPa=r['E'],p_allow_MPa=r['p']) for r in reversed(model['parts'])]
    w=model['washer'];n=model['nut']
    result=calculate(upper_raw,free,p,dict(thickness_mm=w['t'],inner_mm=w['ID'],outer_mm=w['OD'],E_GPa=w['E'],p_allow_MPa=w['p']),dict(height_mm=n['h'],bearing_inner_mm=n['ID'],bearing_outer_mm=n['OD'],p_allow_MPa=n['p']),target,snug,mu_g,mu_k,closure,lower_raw,_variable=True)
    for row,source in zip(result['stud'],free):row['ID']=source['ID']+' free'
    f=result['target_n'];f0=result['snug_preload_n'];mt=result['thread_torque_nm']*1000;c_thread=mt/f
    engaged=[];male_c=female_c=extra_ct=0
    for end,t,m,s in [('Lower',l,model['anchor'],model['stud'][0]),('Upper',u,model['nut'],model['stud'][-1])]:
      length=m['kg']*t['d_mm'];e=s['E']*1000;area=pi*t['d3_mm']**2/4
      cm=length/(e*area);cf=m['km']*t['d_mm']/(m['E']*1000*pi*t['d_mm']**2/4)
      j=pi*t['d3_mm']**4/32;gt=e/(2*(1+s['nu']));ct=m['Ltors']/(gt*j)
      sigma=f/t['As_mm2'];tau=mt*t['d3_mm']/(2*j);vm=sqrt(sigma*sigma+3*tau*tau)
      engaged.append(dict(end=end,physical_engagement_mm=g[end.lower()+'_engagement'],male_equivalent_mm=length,
         female_equivalent_mm=m['km']*t['d_mm'],male_compliance_mm_n=cm,female_compliance_mm_n=cf,
         torsion_equivalent_mm=m['Ltors'],elongation_mm=f*cm,female_movement_mm=f*cf,
         sigma_MPa=sigma,tau_MPa=tau,vm_MPa=vm,yield_factor=s['Rp']/vm))
      male_c+=cm;female_c+=cf;extra_ct+=ct
      capacity=s['Rp']/sqrt((1/t['As_mm2'])**2+3*(c_thread*t['d3_mm']/(2*j))**2)
      result['elastic_limit_n']=min(result['elastic_limit_n'],capacity)
    result['free_stud_compliance_mm_n']=result['stud_compliance_mm_n']
    result['stud_compliance_mm_n']+=male_c
    result['female_compliance_mm_n']=female_c
    result['stud_stiffness_n_mm']=1/result['stud_compliance_mm_n']
    result['joint_compliance_mm_n']+=male_c+female_c
    result['joint_stiffness_n_mm']=1/result['joint_compliance_mm_n']
    result['torsion_compliance_rad_nmm']+=extra_ct
    result['stud_elongation_mm']=f*result['stud_compliance_mm_n']
    result['female_movement_mm']=f*female_c
    result['helix_angle_deg']=360*((f-f0)*result['joint_compliance_mm_n']+closure/1000)/u['pitch_mm']
    result['twist_increment_deg']=degrees((f-f0)*c_thread*result['torsion_compliance_rad_nmm'])
    result['angle_deg']=result['helix_angle_deg']+result['twist_increment_deg']
    result['stud_twist_deg']=degrees(mt*result['torsion_compliance_rad_nmm'])
    result['max_vm_MPa']=max([result['max_vm_MPa']]+[e['vm_MPa'] for e in engaged])
    result['min_yield_factor']=min([result['min_yield_factor']]+[e['yield_factor'] for e in engaged])
    result['elastic_ok']=f<=result['elastic_limit_n'];result['instruction_valid']=result['elastic_ok'] and result['pressure_ok']
    # No service load fraction for this mixed support-compliance approximation.
    result.pop('ideal_load_fraction',None)
    result['engaged']=engaged;result['decomposition']=g['segments'];result['geometry']=g
    return result
