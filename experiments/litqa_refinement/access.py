"""Audited exact file grants for trusted coordinators and narrow model actors.

This is a Python file-access guard, not an OS sandbox for hostile native code.
An actor receives its in-memory typed descriptor and cannot open coordinator
inputs. Generated text has no file/tool API. Roles remain explicit in the log.
"""
from contextlib import contextmanager
import encodings.idna  # Load the loopback hostname codec before file auditing.
import os
from pathlib import Path
import sys
import threading

from tether_engine.serde import canonical
from .contracts import need


def _key(path):return str(Path(path).resolve()).casefold()


class RoleAudit:
    def __init__(self,*,inputs,code_files,runtime_roots,model_files,output):
        self.inputs=frozenset(_key(p) for p in inputs)
        self.code=frozenset(_key(p) for p in code_files)
        self.models=frozenset(_key(p) for p in model_files)
        self.runtime=tuple(Path(p).resolve() for p in runtime_roots)
        approved={Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve()}
        need(set(self.runtime)<=approved,'Only exact interpreter runtime roots are allowed')
        self.output=Path(output).resolve();self.actor_output=None
        self.role='coordinator';self.active=False;self.local=threading.local()
        self.denials=0;self.opens=0
        self.stream=(self.output/'io-audit.jsonl').open('xb',buffering=0)

    def hook(self,event,args):
        if not self.active or event!='open' or getattr(self.local,'busy',False):return
        self.local.busy=True
        try:
            name,mode,flags=args
            if isinstance(name,int):
                row=dict(path=None,descriptor=name,mode=mode,flags=flags,allowed=True,basis='existing_descriptor',role=self.role)
            else:
                path=Path(os.fsdecode(name)).resolve();key=_key(path)
                write=bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
                target=self.output if self.role=='coordinator' else self.actor_output
                own=path.is_relative_to(target)
                shared=key in self.code or key in self.models or any(path.is_relative_to(p) for p in self.runtime)
                explicit=self.role=='coordinator' and key in self.inputs
                allowed=own or (not write and (shared or explicit))
                basis='role_output' if own else 'code_model_runtime' if shared and not write else 'coordinator_input' if explicit and not write else 'denied'
                row=dict(path=str(path),mode=mode,flags=flags,allowed=allowed,basis=basis,role=self.role)
            self.stream.write(canonical(row)+b'\n');self.opens+=1
            if not row['allowed']:
                self.denials+=1;os.fsync(self.stream.fileno())
                raise PermissionError('Undeclared '+self.role+' file access: '+str(row['path']))
        finally:self.local.busy=False

    def activate(self):
        need(not self.active,'Role audit already active')
        sys.addaudithook(self.hook);self.active=True

    @contextmanager
    def actor(self,task,output):
        need(self.active and self.role=='coordinator' and task in ('critic','repair','removal'),'Invalid actor scope')
        target=Path(output).resolve();need(target!=self.output and target.is_relative_to(self.output),'Actor output must be a strict child')
        self.actor_output=target;self.role=task
        self.stream.write(canonical(dict(event='actor_entered',role=task,output=str(target),coordinator_inputs_granted=False))+b'\n')
        try:yield
        finally:
            self.stream.write(canonical(dict(event='actor_exited',role=task,output=str(target)))+b'\n')
            self.role='coordinator';self.actor_output=None

    def flush(self):self.stream.flush();os.fsync(self.stream.fileno())
