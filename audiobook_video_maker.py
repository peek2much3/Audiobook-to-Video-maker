#!/usr/bin/env python3
"""Linux Tkinter GUI for creating audiobook videos with FFmpeg."""
import os, queue, shlex, shutil, subprocess, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox

class App:
    def __init__(self, root):
        self.root = root
        root.title("Audiobook to Video Maker")
        root.geometry("820x650")
        self.q = queue.Queue()
        self.worker = None
        self.cover = tk.StringVar()
        self.audio = tk.StringVar()
        self.logo = tk.StringVar()
        self.output = tk.StringVar(value=os.path.abspath("Book.mp4"))
        self.width = tk.StringVar(value="100")
        self.margin = tk.StringVar(value="40")
        self.key_black = tk.BooleanVar(value=True)
        self.preset = tk.StringVar(value="medium")
        self.crf = tk.StringVar(value="23")
        self.status = tk.StringVar(value="Ready")
        self.ui()
        root.after(100, self.poll)

    def ui(self):
        f = ttk.Frame(self.root, padding=14); f.pack(fill="both", expand=True)
        ttk.Label(f, text="Audiobook to Video Maker", font=("TkDefaultFont", 17, "bold")).pack(anchor="w")
        ttk.Label(f, text="Create a 1920×1080 MP4 from a cover and audio, with an optional Subscribe overlay.").pack(anchor="w", pady=(2,12))
        files = ttk.LabelFrame(f, text="Files", padding=10); files.pack(fill="x")
        self.file_row(files, 0, "Cover image", self.cover, self.pick_cover)
        self.file_row(files, 1, "Audio (MP3 / M4B)", self.audio, self.pick_audio)
        self.file_row(files, 2, "Subscribe image (optional)", self.logo, self.pick_logo)
        self.file_row(files, 3, "Output MP4", self.output, self.pick_output)
        opts = ttk.LabelFrame(f, text="Options", padding=10); opts.pack(fill="x", pady=12)
        r = ttk.Frame(opts); r.pack(fill="x", pady=3)
        ttk.Label(r,text="Overlay width (px)").pack(side="left")
        ttk.Entry(r,textvariable=self.width,width=8).pack(side="left",padx=(6,20))
        ttk.Label(r,text="Right/bottom margin (px)").pack(side="left")
        ttk.Entry(r,textvariable=self.margin,width=8).pack(side="left",padx=6)
        ttk.Checkbutton(opts,text="Remove black background from overlay",variable=self.key_black).pack(anchor="w",pady=3)
        r = ttk.Frame(opts); r.pack(fill="x",pady=3)
        ttk.Label(r,text="x264 preset").pack(side="left")
        ttk.Combobox(r,textvariable=self.preset,state="readonly",width=12,
            values=("ultrafast","superfast","veryfast","faster","fast","medium","slow","slower","veryslow")).pack(side="left",padx=6)
        ttk.Label(r,text="CRF").pack(side="left",padx=(18,4))
        ttk.Entry(r,textvariable=self.crf,width=6).pack(side="left")
        actions=ttk.Frame(f); actions.pack(fill="x",pady=(0,10))
        self.go=ttk.Button(actions,text="Generate video",command=self.generate); self.go.pack(side="left")
        ttk.Button(actions,text="Show FFmpeg command",command=self.show_command).pack(side="left",padx=8)
        self.bar=ttk.Progressbar(actions,mode="indeterminate",length=180); self.bar.pack(side="right")
        logf=ttk.LabelFrame(f,text="FFmpeg output",padding=8); logf.pack(fill="both",expand=True)
        self.log=tk.Text(logf,height=14,wrap="word",state="disabled")
        sb=ttk.Scrollbar(logf,command=self.log.yview); self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        ttk.Label(f,textvariable=self.status,relief="sunken",anchor="w").pack(fill="x",pady=(8,0))

    def file_row(self, parent, row, label, var, cmd):
        ttk.Label(parent,text=label,width=25).grid(row=row,column=0,sticky="w",pady=4)
        ttk.Entry(parent,textvariable=var).grid(row=row,column=1,sticky="ew",padx=6,pady=4)
        ttk.Button(parent,text="Browse…",command=cmd).grid(row=row,column=2,pady=4)
        parent.columnconfigure(1,weight=1)

    def pick_cover(self):
        p=filedialog.askopenfilename(filetypes=[("Images","*.jpg *.jpeg *.png *.webp *.bmp"),("All files","*.*")])
        if p:self.cover.set(p)
    def pick_audio(self):
        p=filedialog.askopenfilename(filetypes=[("Audio","*.mp3 *.m4b *.m4a *.aac *.wav *.flac"),("All files","*.*")])
        if p:
            self.audio.set(p)
            if not self.output.get() or self.output.get()==os.path.abspath("Book.mp4"):
                self.output.set(os.path.join(os.path.dirname(p),os.path.splitext(os.path.basename(p))[0]+".mp4"))
    def pick_logo(self):
        p=filedialog.askopenfilename(filetypes=[("Images","*.png *.webp *.jpg *.jpeg"),("All files","*.*")])
        if p:self.logo.set(p)
    def pick_output(self):
        p=filedialog.asksaveasfilename(defaultextension=".mp4",filetypes=[("MP4 video","*.mp4")])
        if p:self.output.set(p)

    def command(self):
        cover,audio,logo,out=[v.get().strip() for v in (self.cover,self.audio,self.logo,self.output)]
        if not cover or not os.path.isfile(cover): raise ValueError("Choose an existing cover image.")
        if not audio or not os.path.isfile(audio): raise ValueError("Choose an existing audio file.")
        if logo and not os.path.isfile(logo): raise ValueError("Subscribe image was not found.")
        if not out: raise ValueError("Choose an output MP4 file.")
        crf=int(self.crf.get())
        if not 0<=crf<=51: raise ValueError("CRF must be between 0 and 51.")
        cmd=["ffmpeg","-y","-loop","1","-framerate","1","-i",cover,"-i",audio]
        if logo:
            w,m=int(self.width.get()),int(self.margin.get())
            if not 20<=w<=1920 or not 0<=m<=1000: raise ValueError("Check overlay width (20–1920) and margin (0–1000).")
            cmd += ["-loop","1","-framerate","1","-i",logo]
            key="colorkey=0x000000:0.18:0.08," if self.key_black.get() else ""
            filt=(f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                  "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,format=rgba[bg];"
                  f"[2:v]scale={w}:-1,format=rgba,{key}format=rgba[logo];"
                  f"[bg][logo]overlay=W-w-{m}:H-h-{m}:format=auto,format=yuv420p[v]")
        else:
            filt=("[0:v]scale=1920:1080:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                  "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p[v]")
        cmd += ["-filter_complex",filt,"-map","[v]","-map","1:a:0","-c:v","libx264",
                "-preset",self.preset.get(),"-tune","stillimage","-r","1","-crf",str(crf),
                "-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",out]
        return cmd

    def show_command(self):
        try: s=shlex.join(self.command())
        except Exception as e: messagebox.showerror("Settings",str(e)); return
        w=tk.Toplevel(self.root); w.title("FFmpeg command"); w.geometry("760x250")
        t=tk.Text(w,wrap="word"); t.pack(fill="both",expand=True,padx=8,pady=8); t.insert("1.0",s); t.configure(state="disabled")

    def append(self,s):
        self.log.configure(state="normal"); self.log.insert("end",s); self.log.see("end"); self.log.configure(state="disabled")

    def generate(self):
        if self.worker and self.worker.is_alive(): return
        if not shutil.which("ffmpeg"): messagebox.showerror("FFmpeg missing","Install FFmpeg and ensure it is in PATH."); return
        try: cmd=self.command()
        except Exception as e: messagebox.showerror("Check settings",str(e)); return
        os.makedirs(os.path.dirname(os.path.abspath(self.output.get())),exist_ok=True)
        self.log.configure(state="normal"); self.log.delete("1.0","end"); self.log.configure(state="disabled")
        self.append("Running:\n"+shlex.join(cmd)+"\n\n")
        self.go.configure(state="disabled"); self.bar.start(12); self.status.set("Generating video…")
        self.worker=threading.Thread(target=self.run,args=(cmd,),daemon=True); self.worker.start()

    def run(self,cmd):
        try:
            p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
            for line in p.stdout:self.q.put(("log",line))
            self.q.put(("done",p.wait()))
        except Exception as e:self.q.put(("error",str(e)))

    def poll(self):
        try:
            while True:
                kind,val=self.q.get_nowait()
                if kind=="log":self.append(val)
                elif kind=="done":
                    self.bar.stop(); self.go.configure(state="normal")
                    if val==0:
                        self.status.set("Completed successfully"); messagebox.showinfo("Done","Audiobook to video created successfully.")
                    else:
                        self.status.set(f"FFmpeg exited with code {val}")
                        messagebox.showerror("FFmpeg error",f"FFmpeg exited with code {val}. See the output log.")
                else:
                    self.bar.stop(); self.go.configure(state="normal"); self.status.set("Error"); messagebox.showerror("Error",val)
        except queue.Empty:pass
        self.root.after(100,self.poll)

if __name__=="__main__":
    root=tk.Tk()
    try:
        style=ttk.Style()
        if "clam" in style.theme_names():style.theme_use("clam")
    except tk.TclError:pass
    App(root); root.mainloop()
