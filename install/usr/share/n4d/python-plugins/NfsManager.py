#!/usr/bin/python3
import subprocess
import re
import os
import tempfile
from jinja2 import Environment
from jinja2.loaders import FileSystemLoader
from jinja2 import Template
import n4d.responses


class NfsManager:

	#ERRORS CODE
	remove_ip_from_share_error = -10

	
	def __init__(self):
		
		self.nfs_dir="/etc/exports.d/"
		self.nfs_file=self.nfs_dir+"net.exports"
		self.mirror_file=self.nfs_dir+"mirror.exports"
		self.default_options="rw,async,no_subtree_check,no_root_squash"
		self.regex_pattern="^(/[\-/\w]+)(\s+)((((\d{1,3}\.){3}\d{1,3})|[a-zA-Z0-9\.\*]+)\((.*)\)(\s+|$))+"
		self.file_header="#\n# File generated by NfsManager plugin. Do not edit\n#\n\n"
		
		self.default_mount_options="rw,hard,intr,nosuid,nfsvers=3"
		self.tpl_env = Environment(loader=FileSystemLoader('/usr/share/n4d/templates/nfs'))
		
		self.backup_files=[r'/lib/systemd/system/net-server\x2dsync.mount']
		self.backup_dirs=["/etc/exports.d/"]


		# LLX TESTING
		#self.nfs_file="/tmp/exports"
		#
		
		if not os.path.exists(self.nfs_dir):
			os.makedirs(self.nfs_dir)
		
	#def __init__
		
		
	def parse_exports_file(self,f=None):
		
		if f==None:
			f=self.nfs_file

		if not os.path.isfile(f):
			#Old n4d: return {}
			# build_successful_call_response(ret_value=True,ret_msg=HUMAN_RESPONSES[CALL_SUCCESSFUL],status_code=0)
			return n4d.responses.build_successful_call_response({})
		
		f=open(f)
		lines=f.readlines()
		f.close()
		
		exports={}
		
		for line in lines:
			ret=re.match(self.regex_pattern,line)
			if ret:
				d,ip_list=ret.group(1),ret.group(3)
				
				for info in ip_list.split(" "):
					info=info.strip("\n")
					info=info.split("(")
					ip=info[0]
					options=info[1].strip(")")
					
					if d not in exports:
						exports[d]={}
					
					exports[d][ip]=options

		# Old n4d: return exports
		return n4d.responses.build_successful_call_response(exports)
	
	#def parse_exports_file
	

	def fix_missing_no_root_squash(self):
		
		exports=self.parse_exports_file()['return']
		print(exports)

		for d in exports:
			for ip in exports[d]:
				if "no_root_squash" not in exports[d][ip]:
					exports[d][ip]+=",no_root_squash"
		print('write_exports_file')
		print(exports)
		self.write_exports_file(exports)

	#def fix_missing_no_root_squash
	

	def fix_async(self):

		exports=self.parse_exports_file()['return']
		for d in exports:
			for ip in exports[d]:
				if "async" not in exports[d][ip]:
					if "sync" in exports[d][ip]:
						exports[d][ip]=exports[d][ip].replace("sync","async")
					else:
						exports[d][ip]+=",async"

		self.write_exports_file(exports)

	#def fix_async
	

	def export_directories(self):
		
		#ret=os.system("exportfs -ra")
		p=subprocess.Popen(["exportfs","-ra"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		ret=p.communicate()
		
		if p.poll()==0:
			#old n4d: return {"status":True , "msg": "NFS shares exported"}
			return n4d.responses.build_successful_call_response(True,'NFS shares exported')
			
		else:
			#old n4d: return {"status":False, "msg":ret[1]}
			return n4d.responses.build_failed_call_response(-30,ret[1])
		
	#def export_directories

	
	def add_share(self,d,ip,options=None):
		
		if options==None:
			options=self.default_options
			
		exports=self.parse_exports_file()['return']
	
		if d not in exports:
			exports[d]={}
		exports[d][ip]=options
		return self.write_exports_file(exports)
		
	#def add_share
	
	
	def add_mirror(self,mirror_dir,ip,options=None):
		
		if options==None:
			options=self.default_options
			
		exports=self.parse_exports_file(self.mirror_file)['return']
	
		if mirror_dir not in exports:
			exports[mirror_dir]={}
		exports[mirror_dir][ip]=options
		return self.write_exports_file(exports,self.mirror_file)
		
	#def add_share
	
	
	def remove_ip_from_share(self,share,ip):
		
		exports=self.parse_exports_file()['return']
		
		if share in exports:
			if ip in exports[share]:
				exports[share].pop(ip)
				
				self.write_exports_file(exports)
				
				#Old n4d: return {"status":True,"msg":"Removed IP from server"}
				return n4d.responses.build_successful_call_response(True,"Removed IP from server")
			
			else:
				#Old n4d: return {"status":False,"msg":"IP not found"}
				return n4d.responses.build_successful_call_response(False,"IP not found")
				
		else:
			#Old n4d: return {"status":True,"msg":"Share dir. not found"}
			return n4d.responses.build_successful_call_response(True,"Share dir. not found")
			
		
	#def remove_ip_from_share
	
	
	def remove_ip_from_mirror(self,mirror_dir,ip):
		
		exports=self.parse_exports_file(self.mirror_file)['return']
		
		if mirror_dir in exports:
			if ip in exports[mirror_dir]:
				exports[mirror_dir].pop(ip)
				
				self.write_exports_file(exports,self.mirror_file)
				
				#Old n4d: return {"status":True,"msg":"Removed IP from server"}
				return n4d.responses.build_successful_call_response(True,"Removed IP from server")
			
			else:
				#Old n4d: return {"status":False,"msg":"IP not found"}
				return n4d.responses.build_successful_call_response(False,"IP not found")
				
		else:
			#Old n4d: return {"status":True,"msg":"Share dir. not found"}
			return n4d.responses.build_successful_call_response(True,"Share dir. not found")
			
		
	#def remove_ip_from_share
	
	
	
	def write_exports_file(self,exports,f=None):

		
		if f==None:
			f=self.nfs_file
			
		file_lines=[]
		file_lines.append(self.file_header)
			
		for d in exports:
			line="%s\t\t%s\n"
			ip_list=""
			if len(exports[d]) ==0:
				continue
			for ip in exports[d]:
				ip_list+="%s(%s) "%(ip,exports[d][ip])
			ip_list=ip_list.rstrip(" ")
			file_lines.append(line%(d,ip_list))
			
		file_lines.append("\n")
		
		f=open(f,"w")
		for line in file_lines:
			f.write(line)
		f.close()

		export_value=self.export_directories()['status']
		if export_value == 0:
			#Old n4d: return {"status":True,"msg":"NFS exports.d file written"}
			return n4d.responses.build_successful_call_response(True,"NFS exports.d file written")
		else:
			print('fracaso')
			return n4d.responses.build_successful_call_response(False,"NFS exports.d can't file written")

			
	#def write_exports_file
	
	
	def configure_mount_on_boot(self,source,target,options=None):
		
		if options==None:
			options=self.default_mount_options
			
		
		template_cname = self.tpl_env.get_template("mount.skel")
		list_variables = {}
		list_variables["SRC"]=source
		list_variables["DEST"]=target
		list_variables["OPTIONS"]=options
		
		string_template = template_cname.render(list_variables).encode('UTF-8')
		
		fd, tmpfilepath = tempfile.mkstemp()
		new_export_file = open(tmpfilepath,'w')
		new_export_file.write(string_template)
		new_export_file.close()
		os.close(fd)
		
		p=subprocess.Popen(["systemd-escape",target.lstrip("/")],stdout=subprocess.PIPE)
		file_name=p.communicate()[0].strip("\n")+".mount"
		file_dest="/lib/systemd/system/"+file_name
		
		n4d_mv(tmpfilepath,file_dest,True,'root','root','0644',False )
		
		os.system("systemctl daemon-reload")
		o=subprocess.Popen(["systemctl","enable",file_name],stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		o2=subprocess.Popen(["systemctl","start",file_name],stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		
		ret=(o,o2)
		
		#Old n4d: return {"status":True,"msg":ret}
		return n4d.responses.build_successful_call_response(True,ret)
		
	#def configure_mount_on_boot
	
	
	def remove_mount_on_boot(self,target):
		
		p=subprocess.Popen(["systemd-escape",target.lstrip("/")],stdout=subprocess.PIPE)
		file_name=p.communicate()[0].strip("\n")+".mount"
		file_dest="/lib/systemd/system/"+file_name
		
		ret=""
		
		if os.path.exists(file_dest):
			o2=subprocess.Popen(["systemctl","stop",file_name],stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			o=subprocess.Popen(["systemctl","disable",file_name],stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			os.remove(file_dest)
			ret=(o,o2)
			
		#Old n4d: return {"status":True,"msg":ret}
		return n4d.responses.build_successful_call_response(True,ret)
		
	#def remove_mount_on_boot
	
	
	def is_mount_configured(self,target):
		
		p=subprocess.Popen(["systemd-escape",target.lstrip("/")],stdout=subprocess.PIPE)
		file_name=p.communicate()[0].strip("\n")+".mount"
		file_dest="/lib/systemd/system/"+file_name
		
		if os.path.exists(file_dest):
			#Old n4d: return {"status":True,"msg":"Mount systemd configuration exists"}
			return n4d.responses.build_successful_call_response(True,"Mount systemd configuration exists")
		else:
			#Old n4d: return {"status":False,"msg":"Mount systemd configuration doesn't exist"}
			return n4d.responses.build_successful_call_response(False,"Mount systemd configuration doesn't exist")
		
	#def is_mount_configured
	
	
	def is_mirror_shared(self,mirror_path,ip=None):
		
		exports=self.parse_exports_file(self.mirror_file)['return']
		
		if mirror_path not in exports:
			#Old n4d: return {"status":False, "msg": "Shared path not found"}
			return n4d.responses.build_successful_call_response(False,"Shared path not found")
		
		if ip!=None:
			if ip not in exports[mirror_path]:
				#Old n4d: return {"status":False, "msg": "IP not configured in shared path"}
				return n4d.responses.build_successful_call_response(False,"IP not configured in shared path")
		
		#Old n4d: return {"status": True, "msg": "Shared is configured"}
		return n4d.responses.build_successful_call_response(True,"Shared is configured")
		
	#def is_mirror_shared
	
	
	def clean_exports_file(self,f=None):
		
		if f==None:
			f=self.nfs_file
		
		if os.path.exists(f):
			os.remove(f)
			self.export_directories()
		
		#Old n4d: return {"status":True,"msg":"NfsManager exports.d file is now clean"}
		return n4d.responses.build_successful_call_response(True,"NfsManager exports.d file is now clean")

	#def clean_exports_file


	def makedir(self,dir_path=None):

		if not os.path.isdir(dir_path):
			os.makedirs(dir_path)
		#Old n4d: return [True]
		return n4d.responses.build_successful_call_response(True)
		
	#def makedir
	
	
	def backup(self,dir_path="/backup"):
		try:
			self.makedir(dir_path)
			#get_backup_name es una funcion que esta definida en n4d
			file_path=dir_path+"/"+get_backup_name("NfsManager")

			tar=tarfile.open(file_path,"w:gz")
			for f in self.backup_files:
				if os.path.exists(f):
					tar.add(f)
			for d in self.backup_dirs:
				if os.path.exists(d):
					for f in os.listdir(d):
						tar.add(d+f)

			tar.close()
			print ("Backup generated in %s" % file_path)
			#Old n4d: return [True,file_path]
			return n4d.responses.build_successful_call_response(file_path)

		except Exception as e:
			print ("Backup failed", e)
			#Old n4d: return [False,str(e)]
			return n4d.responses.build_failed_call_response(-10,str(e))

	#def backup


	def restore(self,file_path=None):

		#Ordeno de manera alfabetica el directorio y busco el fichero que tiene mi cadena
		if file_path==None:
			dir_path="/backup"
			for f in sorted(os.listdir(dir_path),reverse=True):
				if "NfsManager" in f:
					file_path=dir_path+"/"+f
					break

		#Descomprimo el fichero y solo las cadenas que espero encontrar son las que restauro, reiniciando el servicio
		try:
			if os.path.exists(file_path):
				tmp_dir=tempfile.mkdtemp()
				tar=tarfile.open(file_path)
				tar.extractall(tmp_dir)
				tar.close()

				for f in self.backup_files:
						tmp_path=tmp_dir+f
						if os.path.exists(tmp_path):
							shutil.copy(tmp_path,f)

				for d in self.backup_dirs:
					tmp_path=tmp_dir+d	
					if os.path.exists(tmp_path):
						cmd="cp -r " + tmp_path + "/* " + d
						if not os.path.exists(d):
							os.makedirs(d)
						os.system(cmd)

			print ("File is restored in %s" % self.backup_files)
			#Old n4d: return [True,""]
			return n4d.responses.build_successful_call_response(file_path)

		except Exception as e:

			print ("Restored failed", e)
			#Old n4d: return [False,str(e)]
			return n4d.responses.build_failed_call_response(-20,str(e))

	#def restore
	
	
	
	
#class NfsManager

if __name__=="__main__":
	
	pass


