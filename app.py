"""StudLab 1.2 — bottom-up physical geometry and a focus-aware geometry editor."""
from pathlib import Path
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from mechanics import thread_geometry
from physical import defaults,analyse,solve
from physical_diagram import svg

ROOT=Path(__file__).parent
st.set_page_config(page_title='StudLab',page_icon='🔩',layout='wide')
st.markdown('<style>.block-container{padding-top:2rem;max-width:1650px}h3{padding-top:.5rem}</style>',unsafe_allow_html=True)
st.title('StudLab · bottom-up physical decomposition')
st.caption('Version 1.2 · physical geometry ≠ elastic substitute lengths · VDI-oriented prototype')
with st.expander('README · model and scope'):
    st.markdown((ROOT/'README.md').read_text())
threads=json.loads((ROOT/'threads.json').read_text())['threads'];byname={r['name']:r for r in threads};names=list(byname)
a,b,c,d=st.columns(4)
with a:upper_name=st.selectbox('Upper external / nut thread',names,index=names.index('M10 × 1.5'),key='upper_thread')
with b:lower_name=st.selectbox('Lower external / anchor thread',names,index=names.index('M10 × 1.5'),key='lower_thread')
with c:target=st.number_input('Target tension (N)',min_value=1.,value=20000.,step=1000.,format='%.0f',key='target')
with d:snug=st.number_input('Snug torque (N·m)',min_value=0.,value=10.,step=1.,format='%.1f',key='snug')
u=thread_geometry(byname[upper_name]);u['name']=upper_name;l=thread_geometry(byname[lower_name]);l['name']=lower_name
a,b,c=st.columns(3)
with a:mu_g=st.number_input('μG · thread friction',min_value=0.,max_value=1.,value=.12,step=.01,format='%.3f',key='mu_g')
with b:mu_k=st.number_input('μK · nut / washer friction',min_value=0.,max_value=1.,value=.12,step=.01,format='%.3f',key='mu_k')
with c:closure=st.number_input('Additional seating closure (µm)',min_value=0.,value=0.,step=1.,format='%.0f',key='closure')
if 'physical_model' not in st.session_state:st.session_state.physical_model=defaults(u,l)
if 'editor_revision' not in st.session_state:st.session_state.editor_revision=0
if st.button('Reset physical geometry to selected threads'):
    st.session_state.physical_model=defaults(u,l);st.session_state.editor_revision+=1;st.session_state.pop('edit_token',None);st.rerun()
m=st.session_state.physical_model;g=analyse(m,u,l)
st.info('Origin z = 0 is shared by the lower male thread and tapped hole. Their separate ends define the following intervals. Plain body segments and clamped parts can be added or removed. Protrusion or unused female thread is allowed when the actual engagement remains sufficient for the entered equivalent lengths. Interference with an unthreaded body is checked.')
st.caption('Axial reference factors are editable: male engaged region 0.5d, female nut region 0.4d, female tapped region 0.33d. Applicability to this stud design still needs verification against your VDI edition. Engaged torsional equivalent lengths are separate inputs, default 0 mm (end-region twist omitted). No thread stripping verification.')
editor=components.declare_component('studlab_geometry_editor',path=str(ROOT/'editor'))
value=editor(model=m,svg=svg(m,u,l,g),suggestions=g['suggestions'],has_length_error=any(any(word in i['message'].lower() for word in ('length','begins','ends','coverage','engagement','interferes','no upper')) for i in g['issues']),default=None,key='physical_editor_'+str(st.session_state.editor_revision))
if isinstance(value,dict) and value.get('token')!=st.session_state.get('edit_token'):
    candidate=value.get('model')
    if isinstance(candidate,dict) and all(k in candidate for k in ('stud','parts','washer','nut','anchor')):
        st.session_state.physical_model=candidate;st.session_state.edit_token=value.get('token');st.rerun()
for issue in g['issues']:st.error(issue['message'])
for warning in g['warnings']:st.warning(warning)
if g['segments']:
    with st.expander('C intervals · intersection of both physical geometries',expanded=False):
        st.table([{'Interval':f'C{i+1}','z start (mm)':f"{s['z0']:.3f}",'z end (mm)':f"{s['z1']:.3f}",'L (mm)':f"{s['L']:.3f}",'Stud':s['stud'],'Opposite':s['opposite'],'Role':s['state']} for i,s in enumerate(g['segments'])])
        st.caption('Each end of a stud segment, tap, part, washer or nut creates an interval. These intervals are not added as extra springs: free regions and engaged equivalents are counted once.')
if g['issues']:
    st.warning('Geometry is not yet consistent. Focus a length field in the editor to see a proposed correction; other checks may remain after applying it.')
    st.stop()
try:r=solve(m,byname[upper_name],byname[lower_name],target,snug,mu_g,mu_k,closure)
except (ValueError,TypeError,KeyError,OverflowError,ZeroDivisionError) as exc:st.error(str(exc));st.stop()
st.subheader('Torque + angle · end of tightening')
if not r['instruction_valid']:st.error('Target exceeds an entered elastic or pressure limit. Detailed outputs are elastic extrapolations; no valid tightening instruction.')
st.table([
 {'Result':'Angle after snug','Value':f"{r['angle_deg']:.1f} °" if r['instruction_valid'] else 'Unavailable — check limits'},
 {'Result':'Predicted final torque','Value':f"{r['final_torque_nm']:.1f} N·m" if r['instruction_valid'] else 'Unavailable — check limits'},
 {'Result':'Tension at snug','Value':f"{r['snug_preload_n']:.0f} N"},
 {'Result':'Helical angle / additional stud twist','Value':f"{r['helix_angle_deg']:.1f} ° / {r['twist_increment_deg']:.1f} °"},
 {'Result':'Thread / bearing torque','Value':f"{r['thread_torque_nm']:.1f} / {r['bearing_torque_nm']:.1f} N·m"}])
st.caption('Torsion is driven by thread torque MG only. The free span carries full MG; engaged-end twist uses the separate entered torsion-equivalent lengths. Axial substitution factors are not silently used as torsion factors. Output tension is before tool release and later settlement.')
with st.expander('Engaged regions · physical length, equivalent length and elastic movement',expanded=True):
    st.table([{'End':e['end'],'Physical engagement (mm)':f"{e['physical_engagement_mm']:.3f}",'Male axial Leq (mm)':f"{e['male_equivalent_mm']:.3f}",'Female axial Leq (mm)':f"{e['female_equivalent_mm']:.3f}",'Male elongation (mm)':f"{e['elongation_mm']:.3f}",'Female movement (mm)':f"{e['female_movement_mm']:.3f}",'Torsion Leq (mm)':f"{e['torsion_equivalent_mm']:.3f}",'σvM nominal (MPa)':f"{e['vm_MPa']:.1f}",'Rp/σvM':f"{e['yield_factor']:.2f}"} for e in r['engaged']])
with st.expander('Stiffness and total displacements',expanded=True):
    st.table([
      {'Element':'Stud · free + engaged male equivalents','k (N/mm)':f"{r['stud_stiffness_n_mm']:.0f}",'C (µm/kN)':f"{r['stud_compliance_mm_n']*1e6:.3f}",'Movement (mm)':f"{r['stud_elongation_mm']:.3f}"},
      {'Element':'Nut + anchor female equivalents','k (N/mm)':f"{1/r['female_compliance_mm_n']:.0f}" if r['female_compliance_mm_n'] else 'Rigid','C (µm/kN)':f"{r['female_compliance_mm_n']*1e6:.3f}",'Movement (mm)':f"{r['female_movement_mm']:.3f}"},
      {'Element':'Clamped parts + washer','k (N/mm)':f"{r['parts_stiffness_n_mm']:.0f}",'C (µm/kN)':f"{r['parts_compliance_mm_n']*1e6:.3f}",'Movement (mm)':f"{r['parts_contraction_mm']:.3f}"},
      {'Element':'Combined axial compatibility','k (N/mm)':f"{r['joint_stiffness_n_mm']:.0f}",'C (µm/kN)':f"{r['joint_compliance_mm_n']*1e6:.3f}",'Movement (mm)':f"{target*r['joint_compliance_mm_n']:.3f}"}])
    st.caption(f"Stud total twist {r['stud_twist_deg']:.1f}° · washer contraction {r['washer_contraction_mm']:.3f} mm · min Rp/σvM {r['min_yield_factor']:.2f} · peak nominal σvM {r['max_vm_MPa']:.1f} MPa")
with st.expander('Free stud regions · axial / torsional stresses and movements',expanded=False):
    st.dataframe(pd.DataFrame([{'Region':s['ID'],'Free L (mm)':f"{s['length_mm']:.3f}",'k (N/mm)':f"{s['stiffness_n_mm']:.0f}",'G (GPa)':f"{s['G_MPa']/1000:.1f}",'J (mm⁴)':f"{s['J_mm4']:.3f}",'Elongation (mm)':f"{s['elongation_mm']:.3f}",'Twist (°)':f"{s['twist_deg']:.1f}",'σ (MPa)':f"{s['sigma_MPa']:.1f}",'τ (MPa)':f"{s['tau_MPa']:.1f}",'σvM (MPa)':f"{s['vm_MPa']:.1f}"} for s in r['stud']]),hide_index=True,width='stretch')
with st.expander('Clamped parts and bearing pressures',expanded=False):
    st.table([{'Part':p['ID'],'k (N/mm)':f"{p['stiffness_n_mm']:.0f}",'Contraction (mm)':f"{p['contraction_mm']:.3f}",'Compression (MPa)':f"{p['compression_MPa']:.1f}"} for p in r['parts']])
    st.table([{'Interface':'Nut / washer','Pressure (MPa)':f"{r['nut_pressure_MPa']:.1f}"},{'Interface':'Washer / upper part','Pressure (MPa)':f"{r['washer_support_pressure_MPa']:.1f}"}])
st.download_button('Download complete calculation JSON',json.dumps(dict(app='StudLab 1.2',physical_model=m,upper_thread=byname[upper_name],lower_thread=byname[lower_name],results=r),indent=2),file_name='studlab_calculation.json',mime='application/json')
rows=[dict(group='free_stud',**s) for s in r['stud']]+[dict(group='engaged',**e) for e in r['engaged']]+[dict(group='parts',**p) for p in r['parts']]
st.download_button('Download detailed CSV',pd.DataFrame(rows).to_csv(index=False,sep=';'),file_name='studlab_results.csv',mime='text/csv')
