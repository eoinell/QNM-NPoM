# -*- coding: utf-8 -*-
"""
Created on Tue Jun  8 19:32:29 2021

@author: Eoin
"""
from collections import defaultdict
from pathlib import Path
from mim import MIM

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

st.set_page_config(layout="wide")

pi = 3.14159265
def ev_to_wl(eV):
    return 1239.8419300923943/eV
wl_to_ev = ev_to_wl

def wl_to_omega(wl):
    return 2*pi*1239.8419300923943/wl

def Lorentz(wls, center_wl, eff):
    eVs, center_eV = map(wl_to_ev, (wls, center_wl))
    width_2 = MIM(center_eV, n, t)/(1-eff) # eV - = Gamma/2
    lor = (width_2/(width_2**2 + ((eVs-center_eV))**2))/(2*pi**2)
     # 2pi times all eVs for angular frequency, then divide by pi for normalizing
    return lor*eff

def file_to_mode_name(file):
    return file.stem.replace('=', '_').split('_')[1]

def func_maker(args, body_lines, return_value):
    ldict = {}
    defline = f"def func({', '.join(args)}):\n\t"
    body = '\n\t'.join(body_lines)
    returnline = '\treturn ' + return_value
    exec(''.join((defline, body, returnline)), globals(), ldict)
    return ldict['func']

def real_factory(s_expression, parsed_txt):
    return func_maker(('f', 'D', 't', 'n'), [s_expression], parsed_txt)

def imag_factory(parsed_txt):
    func = func_maker(('real', 'D'), [], parsed_txt)

    def inner_func(real, D):
        real = wl_to_ev(real)
        out = func(real, D)
        return 0.00001 if out <= 0 else out  # prevent /0 in Lorentz
    return inner_func

def lorentz_factory(real_eq, imag_eq):
    def inner_func(wl):
        real = real_eq(f, D, t, n)
        efficiency = imag_eq(real, D)
        return Lorentz(wl, real, efficiency)
    return inner_func

def annotate_factory(real_eq, imag_eq):
    def inner_func():
        real = real_eq(f, D, t, n)
        efficiency = imag_eq(real, D)
        return real, efficiency
    return inner_func

@st.cache
def make_modes(folder):
    modes = defaultdict(dict)
    
    for file in (folder / 'real equations').iterdir():
        mode = file_to_mode_name(file)
        
        with open(file, 'r') as eq_file:
            s_expression = eq_file.readline()
            parsed_txt = ''.join(eq_file.read().splitlines())
            modes[f'{mode} mode']['real'] = real_factory(
                s_expression, parsed_txt)
    
    for file in (folder / 'imag equations').iterdir():
        mode = file_to_mode_name(file)
        with open(file, 'r') as eq_file:
            parsed_txt = ''.join(eq_file.read().splitlines())
            modes[f'{mode} mode']['imag'] = imag_factory(parsed_txt)
    
    for mode in modes.values():
        mode['Lorentz'] = lorentz_factory(mode['real'], mode['imag'])
        mode['annotate'] = annotate_factory(mode['real'], mode['imag'])

    def xlim_func():
        reals = [mode['real'](f, D, t, n) for mode in modes.values()]
        return min(reals)*0.93, max(reals)*1.08
    
    return modes, xlim_func

labels = set()
def plot_modes(modes, geometry, resolution=300, coords={}, label=False, xs=[]):
    ys = np.empty((len(modes), resolution))
    for i, (name, mode) in enumerate(modes.items()):
        y =  mode['Lorentz'](xs)
        ys[i] = y
        wl, eff = mode['annotate']()
        _label = f'{name}' #', wl={round(wl)}nm, efficiency={np.around(eff, 2)}'
        
        fig.add_trace(go.Scatter(x=xs, y=y, name=_label, showlegend=(not (_label in labels)),mode='lines', line=dict(color=colors[name],)), **coords)
        labels.add(_label)
    
    fig.add_trace(go.Scatter(x=xs, y=(ys**2/ys.sum(axis=0)).sum(axis=0),
                name='sum' ,showlegend=label, line=dict(color='white', dash='dash',)), **coords)
    fig.update_layout(#title='',
                #    xaxis_title='',
                #    yaxis_title=adjectives[geometry]+' facet', 
                   height=600, width=1100)
    
'''__Qausi-Normal modes of Nanoparticle on mirror__'''
plot_container = st.container()
for col, param, args in zip(st.columns(4), 'fDtn', (('Facet', 0.1, 0.4, 0.3),
                    ('Diameter (nm)', 40., 100., 80.,),
                    ('gap thickness (nm)', 0.75, 6., 1.),
                    ('gap refractive index', 1., 2., 1.5,))):
    with col:
        vars()[param] = st.slider(*args)

adjectives = {'circle': 'circular', 'square': 'square', 'triangle': 'triangular'}
modes = [m+ ' mode' for m in '10 11 20 21 22 2-2'.split()]  
colors = {m: c for m, c in zip(modes, px.colors.qualitative.Plotly )}

@st.cache 
def folders():
    root = Path('geometries')
    return [f for f in root.iterdir() if f.is_dir()]
folders = folders()

with plot_container:
    fig = make_subplots(rows=len(folders), cols=1, 
                        shared_xaxes=True,
                        x_title='wavelength (nm)',
                        y_title='',)
    xs = None
    for i, folder in enumerate(folders):
        modes, xlim_func = make_modes(folder)
        if xs is None: xs = np.linspace(*xlim_func(), 300)
        plot_modes(modes, folder.stem, coords=dict(row=i+1,col=1), label=(folder.stem=='triangle'), xs=xs)  # x axis changes))

    # for i, g in enumerate(folders):
        x = '' if not i else i+1
        fig['layout'][f'yaxis{x}']['title'] = adjectives[folder.name]+' facet' 


 
    st.plotly_chart(fig, use_column_width=True)
'''
__Description of parameters__

__Circle__

f: facet fraction.

The ratio of facet diameter to spherical nanoparticle diameter.
        Range: 0.1-0.4
---------------------------------------------------------------------------
D (nm): Sphere's Diameter.

        Range: 40-100nm        
---------------------------------------------------------------------------
t (nm): gap thickness. 

        Range: 0.75-6nm
---------------------------------------------------------------------------
n: gap refractive index. 

        Range: 1.25-2
---------------------------------------------------------------------------

__Square__

_f_: facet fraction.

Analoguous to the ratio of facet diameter to spherical nanoparticle diameter.
f = $fs/(a(\sqrt2 + 2))$,
where a is Rhombicuboctohedral side length, and fs is the facet side length.
This definition was chosen to preserve the ratio of areas on the facet to the middle 
cross-section of the nanoparticle in the spherical and rhombicuboctohedral cases.
for a regular rhombicuboctohedron, use $1/(\sqrt(2) + 2) ~ 0.29$
        Range: 0.1 - 0.4
---------------------------------------------------------------------------
_D_ (nm): roughly equivalent to Diameter.

A sphere of diameter D and Rhombicuboctohedron
defined by parameter D have the same cross-sectional area.
D = $a/\sqrt(\pi/(12\sqrt3))$
    Range: 40-100nm

__Triangle__

_f_: facet fraction.

Analoguous to the ratio of facet diameter to spherical nanoparticle diameter.
$f = fs/(2\sqrt3 a)$,
where a is Rhombicuboctohedral side length, and fs is the facet side length.
This definition was chosen to preserve the ratio of areas on the facet to the middle 
cross-section of the nanoparticle in the spherical and rhombicuboctohedral cases.
for a regular rhombicuboctohedron, use $1/(2\sqrt3) ~ 0.29$
    Range: 0.1 - 0.4
---------------------------------------------------------------------------
_D_ (nm): roughly equivalent to Diameter.

A sphere of diameter D and Rhombicuboctohedron
defined by parameter D have the same cross-sectional area.
D = $a/\sqrt(\pi/(12\sqrt3))$
    Range: 40-100nm
--------------------------
All geometries have 5nm radius rounding applied to the bottom facet edge.
'''