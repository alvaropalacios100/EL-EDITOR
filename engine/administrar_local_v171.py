"""Panel local (Tkinter), sin cuentas ni servidores: gestiona JSON y TXT reales.
No es el futuro panel web privado. Modifica archivos locales y hace copias .bak.
"""
import json
import re
import shutil
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PRIORIDADES = ROOT / 'prioridades.json'
FUENTES = ROOT / 'fuentes_v06.json'
SECCIONES = {'Editoriales': ROOT/'EDITORIALES', 'El Cinematógrafo': ROOT/'CINEMATOGRAFO'}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def backup_write(path, value):
    if path.exists():
        shutil.copy2(path, str(path)+'.bak')
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)


def save_column(folder, title, date, hour, body):
    title=title.strip();body=body.strip();date=date.strip();hour=hour.strip()
    if not title or not body:raise ValueError('Título y texto son obligatorios.')
    try:datetime.strptime(date+' '+hour,'%Y-%m-%d %H:%M')
    except ValueError:raise ValueError('Fecha/hora inválida. Usa AAAA-MM-DD y HH:MM.')
    if '\n' in title:raise ValueError('El título no puede incluir saltos de línea.')
    folder.mkdir(exist_ok=True)
    slug=re.sub(r'[^a-z0-9]+','-',title.casefold()).strip('-')[:55]
    if not slug:slug='columna'
    file=folder/(date+'_'+slug+'.txt')
    if file.exists():raise FileExistsError('Ya existe una columna con este título y fecha. Edítala manualmente o usa otro título.')
    file.write_text(f'TITULO: {title}\nFECHA_PUBLICACION: {date}\nHORA_PUBLICACION: {hour}\n\n{body}\n',encoding='utf-8')
    return file


class Admin(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('EL EDITOR — Administración local v1.7.1')
        self.geometry('960x690')
        self.minsize(740,560)
        self.topics=read_json(PRIORIDADES)
        self.sources=read_json(FUENTES)
        tabs=ttk.Notebook(self)
        tabs.pack(fill='both',expand=True,padx=12,pady=10)
        self.tabtopics=ttk.Frame(tabs,padding=12)
        self.tabsources=ttk.Frame(tabs,padding=12)
        self.tabcolumns=ttk.Frame(tabs,padding=12)
        tabs.add(self.tabtopics,text='Temas y prioridades')
        tabs.add(self.tabsources,text='Fuentes')
        tabs.add(self.tabcolumns,text='Publicar columnas')
        self.editing_column=None
        self.setup_topics();self.setup_sources();self.setup_columns()
        ttk.Label(self,text='Los cambios en temas y fuentes afectan a futuras recopilaciones. La publicación web aún requiere exportar y subir los archivos.',foreground='#555').pack(pady=(0,10))

    def setup_topics(self):
        bar=ttk.Frame(self.tabtopics);bar.pack(fill='x',pady=4)
        ttk.Label(bar,text='Sección:').pack(side='left')
        self.topicsec=tk.StringVar(value=next(iter(self.topics)))
        sel=ttk.Combobox(bar,textvariable=self.topicsec,values=list(self.topics),state='readonly',width=26)
        sel.pack(side='left',padx=7);sel.bind('<<ComboboxSelected>>',lambda _:self.refresh_topics())
        self.topiclist=ttk.Treeview(self.tabtopics,columns=('tema','prioridad'),show='headings',height=13)
        self.topiclist.heading('tema',text='Tema');self.topiclist.heading('prioridad',text='Prioridad')
        self.topiclist.column('tema',width=530);self.topiclist.column('prioridad',width=120)
        self.topiclist.pack(fill='both',expand=True,pady=5)
        self.topiclist.bind('<<TreeviewSelect>>',lambda _:self.populate_topic())
        form=ttk.Frame(self.tabtopics);form.pack(fill='x',pady=5)
        ttk.Label(form,text='Tema').grid(row=0,column=0,sticky='w')
        self.topicname=tk.StringVar();ttk.Entry(form,textvariable=self.topicname,width=47).grid(row=1,column=0,padx=(0,8),sticky='ew')
        ttk.Label(form,text='Prioridad').grid(row=0,column=1,sticky='w')
        self.priority=tk.StringVar(value='media')
        ttk.Combobox(form,textvariable=self.priority,values=['alta','media','aleatoria'],width=14,state='readonly').grid(row=1,column=1)
        controls=ttk.Frame(self.tabtopics);controls.pack(fill='x',pady=8)
        ttk.Button(controls,text='Añadir o modificar',command=self.set_topic).pack(side='left',padx=(0,8))
        ttk.Button(controls,text='Eliminar seleccionado',command=self.remove_topic).pack(side='left',padx=(0,8))
        ttk.Button(controls,text='Guardar prioridades',command=self.save_topics).pack(side='right')
        self.refresh_topics()

    def refresh_topics(self):
        self.topiclist.delete(*self.topiclist.get_children())
        for name,prio in sorted(self.topics.get(self.topicsec.get(),{}).items(),key=lambda p:p[0].casefold()):
            self.topiclist.insert('', 'end',values=(name,prio))

    def populate_topic(self):
        items=self.topiclist.selection()
        if items:
            name,prio=self.topiclist.item(items[0],'values')
            self.topicname.set(name);self.priority.set(prio)

    def set_topic(self):
        name=self.topicname.get().strip();prio=self.priority.get()
        if not name or prio not in ('alta','media','aleatoria'):return messagebox.showerror('Tema','Introduce un tema y prioridad válidos.')
        sel=self.topiclist.selection()
        if sel:
            old=self.topiclist.item(sel[0],'values')[0]
            if old!=name:self.topics[self.topicsec.get()].pop(old,None)
        self.topics[self.topicsec.get()][name]=prio
        self.refresh_topics()

    def remove_topic(self):
        for item in self.topiclist.selection():
            name=self.topiclist.item(item,'values')[0]
            self.topics[self.topicsec.get()].pop(name,None)
        self.refresh_topics()

    def save_topics(self):
        backup_write(PRIORIDADES,self.topics)
        messagebox.showinfo('Guardado','Prioridades guardadas. Se ha creado una copia .bak.')

    def setup_sources(self):
        ttk.Label(self.tabsources,text='El motor utiliza las fuentes configuradas; algunas también tienen conectores especializados. Verifica que el RSS sea válido.').pack(anchor='w')
        self.sourcelist=ttk.Treeview(self.tabsources,columns=('name','sec','url','mode'),show='headings',height=12)
        for col,label,width in [('name','Medio',155),('sec','Sección',140),('url','URL',400),('mode','Modo',75)]:
            self.sourcelist.heading(col,text=label);self.sourcelist.column(col,width=width)
        self.sourcelist.pack(fill='both',expand=True,pady=8)
        self.sourcelist.bind('<<TreeviewSelect>>',lambda _:self.populate_source())
        frm=ttk.Frame(self.tabsources);frm.pack(fill='x')
        self.sourcevars={}
        for i,(k,label,width) in enumerate([('nombre','Medio',25),('seccion','Sección',23),('url','URL del medio/RSS',65),('modo','Modo',12)]):
            self.sourcevars[k]=tk.StringVar()
            ttk.Label(frm,text=label).grid(row=i,column=0,sticky='w',pady=2)
            ttk.Entry(frm,textvariable=self.sourcevars[k],width=width).grid(row=i,column=1,sticky='ew',pady=2)
        frm.columnconfigure(1,weight=1)
        buttons=ttk.Frame(self.tabsources);buttons.pack(fill='x',pady=8)
        ttk.Button(buttons,text='Añadir/actualizar',command=self.set_source).pack(side='left',padx=4)
        ttk.Button(buttons,text='Eliminar seleccionada',command=self.remove_source).pack(side='left',padx=4)
        ttk.Button(buttons,text='Guardar fuentes',command=self.save_sources).pack(side='right')
        self.refresh_sources()

    def refresh_sources(self):
        self.sourcelist.delete(*self.sourcelist.get_children())
        for i,s in enumerate(self.sources):
            self.sourcelist.insert('', 'end',iid=str(i),values=tuple(s.get(k,'') for k in ('nombre','seccion','url','modo')))

    def populate_source(self):
        sel=self.sourcelist.selection()
        if sel:
            item=self.sources[int(sel[0])]
            for k,var in self.sourcevars.items():var.set(item.get(k,''))

    def set_source(self):
        item={k:v.get().strip() for k,v in self.sourcevars.items()}
        if not item['nombre'] or not item['seccion'] or not item['url'].startswith(('http://','https://')) or item['modo'] not in ('rss','google'):
            return messagebox.showerror('Fuente','Completa medio, sección, URL http(s) y modo rss o google.')
        sel=self.sourcelist.selection()
        if sel:self.sources[int(sel[0])]=item
        else:self.sources.append(item)
        self.refresh_sources()

    def remove_source(self):
        for idx in sorted((int(s) for s in self.sourcelist.selection()),reverse=True):self.sources.pop(idx)
        self.refresh_sources()

    def save_sources(self):
        backup_write(FUENTES,self.sources)
        messagebox.showinfo('Guardado','Fuentes guardadas. Se ha creado una copia .bak.')

    def setup_columns(self):
        ttk.Label(self.tabcolumns,text='Nueva columna programada (hora de Madrid). No se publicará antes de su fecha.').pack(anchor='w',pady=3)
        form=ttk.Frame(self.tabcolumns);form.pack(fill='x',pady=6)
        self.kind=tk.StringVar(value='Editoriales');self.titlevar=tk.StringVar()
        self.datevar=tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.timevar=tk.StringVar(value='08:00')
        ttk.Label(form,text='Colección').grid(row=0,column=0,sticky='w');ttk.Combobox(form,textvariable=self.kind,values=list(SECCIONES),state='readonly',width=24).grid(row=1,column=0,sticky='w',padx=(0,10))
        ttk.Label(form,text='Fecha AAAA-MM-DD').grid(row=0,column=1,sticky='w');ttk.Entry(form,textvariable=self.datevar,width=16).grid(row=1,column=1,sticky='w',padx=(0,10))
        ttk.Label(form,text='Hora HH:MM').grid(row=0,column=2,sticky='w');ttk.Entry(form,textvariable=self.timevar,width=12).grid(row=1,column=2,sticky='w')
        ttk.Label(self.tabcolumns,text='Título').pack(anchor='w',pady=(12,3))
        ttk.Entry(self.tabcolumns,textvariable=self.titlevar).pack(fill='x')
        ttk.Label(self.tabcolumns,text='Texto completo (separa párrafos con una línea vacía)').pack(anchor='w',pady=(12,3))
        self.bodytext=tk.Text(self.tabcolumns,wrap='word',height=15)
        self.bodytext.pack(fill='both',expand=True)
        controls=ttk.Frame(self.tabcolumns);controls.pack(fill='x',pady=10)
        ttk.Button(controls,text='Abrir columna existente',command=self.load_column_ui).pack(side='left')
        ttk.Button(controls,text='Nueva (limpiar)',command=self.clear_column_ui).pack(side='left',padx=8)
        ttk.Button(controls,text='Guardar columna',command=self.save_column_ui).pack(side='right')
        ttk.Label(self.tabcolumns,text='Puedes modificar columnas anteriores desde Abrir columna existente. Se crea una copia .bak al guardar.',foreground='#555').pack(anchor='w')

    def clear_column_ui(self):
        self.editing_column=None
        self.titlevar.set('');self.bodytext.delete('1.0','end')

    def load_column_ui(self):
        folder=SECCIONES[self.kind.get()]
        selected=filedialog.askopenfilename(initialdir=folder,title='Selecciona la editorial o crítica a modificar',filetypes=[('Archivos de texto','*.txt')])
        if not selected:return
        path=Path(selected).resolve()
        if path.parent!=folder.resolve() or path.name=='INSTRUCCIONES.txt':
            return messagebox.showerror('No permitido','Selecciona un archivo de esa colección.')
        try:
            from publicaciones_v164 import parse
            entry=parse(path)
        except (ValueError,OSError) as e:return messagebox.showerror('No se puede abrir',str(e))
        self.editing_column=path
        self.titlevar.set(entry['title']);self.datevar.set(entry['date']);self.timevar.set(entry['time'])
        self.bodytext.delete('1.0','end');self.bodytext.insert('1.0',entry['body'])


    def save_column_ui(self):
        try:
            if self.editing_column:
                f=self.editing_column
                title=self.titlevar.get().strip();date=self.datevar.get().strip();hour=self.timevar.get().strip();body=self.bodytext.get('1.0','end-1c').strip()
                if not title or not body or '\n' in title:raise ValueError('Título y texto son obligatorios.')
                datetime.strptime(date+' '+hour,'%Y-%m-%d %H:%M')
                shutil.copy2(f,str(f)+'.bak')
                f.write_text(f'TITULO: {title}\nFECHA_PUBLICACION: {date}\nHORA_PUBLICACION: {hour}\n\n{body}\n',encoding='utf-8')
            else:
                f=save_column(SECCIONES[self.kind.get()],self.titlevar.get(),self.datevar.get(),self.timevar.get(),self.bodytext.get('1.0','end-1c'))
        except (ValueError,FileExistsError,OSError) as e:return messagebox.showerror('No guardado',str(e))
        messagebox.showinfo('Guardado',f'Guardado {f.name}. Se publicará al regenerar la edición después de la fecha y hora indicada.')

if __name__=='__main__':
    Admin().mainloop()
