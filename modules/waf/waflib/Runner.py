#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2018 (ita)

"""
Runner.py: Task scheduling and execution
"""

import heapq, traceback
try:
	from queue import Queue, PriorityQueue
except ImportError:
	from Queue import Queue
	try:
		from Queue import PriorityQueue
	except ImportError:
		class PriorityQueue(Queue):
			def _init(self, maxsize):
				self.maxsize = maxsize
				self.queue = []
			def _put(self, item):
				heapq.heappush(self.queue, item)
			def _get(self):
				return heapq.heappop(self.queue)

from waflib import Utils, Task, Errors, Logs

GAP = 5
"""
Wait for at least ``GAP * njobs`` before trying to enqueue more tasks to run
"""

### Ao - Added

bc_file_list = []
non_bc_file_list = []
original_task_input_list = []

def is_llvm_bitcode(file_path):
    try:
        with open(file_path, 'rb') as file:
            # Read the first 2 bytes of the file
            magic_number = file.read(2)
            # Check if the magic number matches LLVM bitcode signature ('BC')
            return magic_number == b'BC'
    except IOError:
        # Handle the error if the file cannot be opened
        print("Error opening file.")
        return False
### End - Ao Added


class PriorityTasks(object):
	def __init__(self):
		self.lst = []
	def __len__(self):
		return len(self.lst)
	def __iter__(self):
		return iter(self.lst)
	def clear(self):
		self.lst = []
	def append(self, task):
		heapq.heappush(self.lst, task)
	def appendleft(self, task):
		"Deprecated, do not use"
		heapq.heappush(self.lst, task)
	def pop(self):
		return heapq.heappop(self.lst)
	def extend(self, lst):
		if self.lst:
			for x in lst:
				self.append(x)
		else:
			if isinstance(lst, list):
				self.lst = lst
				heapq.heapify(lst)
			else:
				self.lst = lst.lst

class Consumer(Utils.threading.Thread):
	"""
	Daemon thread object that executes a task. It shares a semaphore with
	the coordinator :py:class:`waflib.Runner.Spawner`. There is one
	instance per task to consume.
	"""
	def __init__(self, spawner, task):
		Utils.threading.Thread.__init__(self)
		self.task = task
		"""Task to execute"""
		self.spawner = spawner
		"""Coordinator object"""
		self.setDaemon(1)
		self.start()
	def run(self):
		"""
		Processes a single task
		"""
		try:
			if not self.spawner.master.stop:
				self.spawner.master.process_task(self.task)
		finally:
			self.spawner.sem.release()
			self.spawner.master.out.put(self.task)
			self.task = None
			self.spawner = None

class Spawner(Utils.threading.Thread):
	"""
	Daemon thread that consumes tasks from :py:class:`waflib.Runner.Parallel` producer and
	spawns a consuming thread :py:class:`waflib.Runner.Consumer` for each
	:py:class:`waflib.Task.Task` instance.
	"""
	def __init__(self, master):
		Utils.threading.Thread.__init__(self)
		self.master = master
		""":py:class:`waflib.Runner.Parallel` producer instance"""
		self.sem = Utils.threading.Semaphore(master.numjobs)
		"""Bounded semaphore that prevents spawning more than *n* concurrent consumers"""
		self.setDaemon(1)
		self.start()
	def run(self):
		"""
		Spawns new consumers to execute tasks by delegating to :py:meth:`waflib.Runner.Spawner.loop`
		"""
		try:
			self.loop()
		except Exception:
			# Python 2 prints unnecessary messages when shutting down
			# we also want to stop the thread properly
			pass
	def loop(self):
		"""
		Consumes task objects from the producer; ends when the producer has no more
		task to provide.
		"""
		master = self.master

		is_intercept = False
		while 1:
			task = master.ready.get()

			 
			### Ao added
			original_task_input_list = task.inputs
			
			import os
			import subprocess
			
			### Check If compile is done
			# if task.keyword() == 'Compiling' and is_intercept:
			# 	task.inputs = original_task_input_list

			# print("[Debug] The task keyword is", task.keyword())

			### Check If compile is done
			if task.keyword() == 'Linking':

				# filter out some case
				substring_to_check = "test.cpp"

				# print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
				# print('[Debug] Task keyword', task.keyword())
				# print("[Debug] Task inputs:", task.inputs)

				# Check if the substring exists in any element of the list
				# for input in task.inputs:
				# 	print("Individual input: ", input, " with the type: ", type(input))
				# 	input_str = str(input)
				# 	print("Individual input: ", input_str, " with the type: ", type(input_str))
				# 	if substring_to_check in input_str:
				# 		print("Found")
				# 	else:
				# 		print("Not found")

				found = any(substring_to_check in str(element) for element in task.inputs)
				found = True

				if found:
					print("Testing. Do nothing")
				else:
					

					########################
					# Link into one bitcode#
					########################

					is_intercept=True
					# Generate the CMPT policy

					for input_bc in task.inputs:
						# opt -f -enable-new-pm=0 -load "$enforce_pass" -HexboxApplication --hexbox-policy="${llvm_output_json_file}"  "$input_ll_file" -o "$output_bc_file"
						input_bc = str(input_bc)
						if is_llvm_bitcode(input_bc):
							bc_file_list.append(input_bc)				
					print("The bc files are: ", bc_file_list)			
					### Hardcode the real path
					
					pwd = os.getcwd()
					one_bitcode_file_path = pwd + '/output.bc'
					print(one_bitcode_file_path)

					# print("After iterating")
					## Link all bc files into one bc
					link_to_one_bc_command = ['llvm-link', '-o', one_bitcode_file_path]
					link_to_one_bc_command = link_to_one_bc_command + bc_file_list

					# print("link_to_one_bc_command : ", link_to_one_bc_command)
					link_to_one_bc_command = " ".join(link_to_one_bc_command)

					print("[Gecko] Linking to one BitCode file")
					print("[Gecko] To execute the command : ", link_to_one_bc_command)
					# Execute the command
					subprocess.run(link_to_one_bc_command, shell=True)
					print("Finished - Linking to one BitCode file", link_to_one_bc_command)

					###################################
					# One bitcode go through LLVM Pass#
					###################################
					
					### Analysis

					input_bc = one_bitcode_file_path
					llvm_path = os.environ["LLVM_DIR"]
					# TODO change hardcode
					# analysis_pass_path = "/home/ao/Projects/recovery/SVF/Release-build/tools/recovery_pass/cpt_analysis/libCMPTAnalysis.so"
					analysis_pass_path = "/home/lab/RedCaPS/SVF/Release-build/tools/recovery_pass/cmpt_analysis/libCMPTAnalysis.so"
					# analysis_result_path = '/home/ao/Projects/redcap_ardupilot/ardupilot/analysis_result.json'
					analysis_result_path = '/home/lab/ardupilot_redcaps/analysis_result.json'
					opt_cmd = llvm_path + '/bin/opt'
					task_name_file ='/tmp/task_cmpt.txt'
					enable_new_pm = '-enable-new-pm=0'
					load_pass = ' -load ' + analysis_pass_path +  ' -HexboxAnaysis --task-names-file=' + task_name_file + '--hexbox-analysis-results=' + analysis_result_path
					analyze_command = [opt_cmd, enable_new_pm, load_pass, input_bc, "-o", input_bc ]

					# Join the command components into a single string (optional)
					analyze_command = " ".join(analyze_command)

					print("Analysis command to run : ", analyze_command)
					# Execute the command
					# jinwen test
					subprocess.run(analyze_command, shell=True)

					print("Finished - Dumping the analysis json")


					### Compartmentalize

					# analyzer_path = '/home/ao/Projects/recovery/compartment/scripts/analyzer.py'
					analyzer_path = '/home/lab/RedCaPS/compartment/scripts/analyzer.py'
					# compartmentalize_result_path = '/home/ao/Projects/redcap_ardupilot/ardupilot/compartment_result.json'
					compartmentalize_result_path = '/home/lab/ardupilot_redcaps/compartment_result.json'
					# link_script_template_path = '/home/ao/Projects/recovery/compartment/ld_templates/x86-template-link-script.ld'
					link_script_template_path = '/home/lab/RedCaPS/compartment/ld_templates/x86-template-link-script.ld'
					# link_script_output_path = '/home/ao/Projects/redcap_ardupilot/ardupilot/link-script.ld'
					link_script_output_path = '/home/lab/ardupilot_redcaps/link-script.ld'
					analysis_pass_option = '-j='+analysis_result_path
					# size_result_option = '-s=../ardupilot/size_result.json'
					size_result_option = '-s=../ardupilot_redcaps/size_result.json'
					compartment_result_option = '-o='+compartmentalize_result_path
					policy_option = '-m=task'
					ld_template_option = "-T="+link_script_template_path
					ld_outout_option = "-L"+link_script_output_path
					compartment_command = ['python3', analyzer_path, analysis_pass_option, size_result_option,
                                            compartment_result_option, policy_option, ld_template_option, ld_outout_option]

					compartment_command = " ".join(compartment_command)
					
					print("Comarptmentalize command to run : ", compartment_command)
					# Execute the command
					# jinwen test
					subprocess.run(compartment_command, shell=True)
					
					### Enforce it
					enforce_bc_folder_path = pwd
					enforce_bc_name = 'enforced.o'
					enforce_bc_path = enforce_bc_folder_path + '/' + enforce_bc_name
					llvm_path = os.environ["LLVM_DIR"]
					# TODO change hardcode
					# partition_pass_path = "/home/ao/Projects/recovery/SVF/Release-build/tools/recovery_pass/cmpt_enforce/libEnforceCMPT.so"
					partition_pass_path = "/home/lab/RedCaPS/SVF/Release-build/tools/recovery_pass/cmpt_enforce/libEnforceCMPT.so"					
					enable_new_pm = '-enable-new-pm=0'
					load_pass = ' -load ' + partition_pass_path +  ' -HexboxApplication --hexbox-policy=' + compartmentalize_result_path
					enforce_command = [opt_cmd, enable_new_pm, load_pass, input_bc, "-o", enforce_bc_path ]

					enforce_command = " ".join(enforce_command)

					print("Enforce command to run : ", enforce_command)
					# Execute the command
					# jinwen test
					subprocess.run(enforce_command, shell=True)
					########


					########################################
					# Link with the transformed one-bitcode#
					########################################

					## Remove some inputs already in one-bitcode
					task.inputs = [item for item in task.inputs if str(item) not in bc_file_list]
					
					print('Finished - Removing tasks that are already in one-bitcodes')
					# print('Remaining tasks: ', str(task.inputs))

					## Append the one-bitcode file
					# task.inputs.append(one_bitcode_file_path)
					
					# Creating the full path for enforced bc
					
					enforced_path = os.path.join(enforce_bc_folder_path, enforce_bc_name)
					task.inputs.append(enforced_path)
					# dir_rt="/home/ao/Projects/recovery/SVF/tools/recovery_pass/cmpt_enforce/link_lib/link_lib.ll"
					dir_rt = os.path.join("/home/ao/Projects/recovery/SVF/tools/recovery_pass/cmpt_enforce/link_lib/", "link_lib.ll") ## TODO fix hardcoded path

					task.inputs.append(dir_rt)
					print('Remaining tasks: ', str(task.inputs))

					# for input_bc in task.inputs:

					# 	# Construct the full command as a list

					# 	input_bc = str(input_bc)
					# 	llvm_path = os.environ["LLVM_DIR"]
					# 	# TODO change hardcode
					# 	analysis_pass_path = "/home/ao/Projects/recovery/SVF/Release-build/tools/recovery_pass/cpt_analysis/libCMPTAnalysis.so"
					# 	partition_pass_path = "/home/ao/Projects/recovery/SVF/Release-build/tools/recovery_pass/cmpt_enforce/libEnforceCMPT.so"
					# 	policy_path = '/home/ao/Projects/recovery/outputs/analysis_result.json'
					# 	opt_cmd = llvm_path + '/bin/opt'
					# 	enable_new_pm = '-enable-new-pm=0'
					# 	load_pass = '-load ' + partition_pass_path +  ' -HexboxApplication --hexbox-policy=' + policy_path
					# 	command = [opt_cmd, enable_new_pm, load_pass, input_bc, "-o", input_bc]

					# 	# Join the command components into a single string (optional)
					# 	full_command = " ".join(command)

					# 	print("The command to run : ", full_command)
					# 	# Execute the command
					# 	subprocess.run(full_command, shell=True)
						

					# pass LLVM pass using opt command
				
			# print("[Debug] Runner.py. I am out of the if loop.")

			### End - instrumentation


			self.sem.acquire()
			if not master.stop:
				task.log_display(task.generator.bld)
			Consumer(self, task)
			
			### Set the task inputs back
			task.inputs = original_task_input_list


class Parallel(object):
	"""
	Schedule the tasks obtained from the build context for execution.
	"""
	def __init__(self, bld, j=2):
		"""
		The initialization requires a build context reference
		for computing the total number of jobs.
		"""

		self.numjobs = j
		"""
		Amount of parallel consumers to use
		"""

		self.bld = bld
		"""
		Instance of :py:class:`waflib.Build.BuildContext`
		"""

		self.outstanding = PriorityTasks()
		"""Heap of :py:class:`waflib.Task.Task` that may be ready to be executed"""

		self.postponed = PriorityTasks()
		"""Heap of :py:class:`waflib.Task.Task` which are not ready to run for non-DAG reasons"""

		self.incomplete = set()
		"""List of :py:class:`waflib.Task.Task` waiting for dependent tasks to complete (DAG)"""

		self.ready = PriorityQueue(0)
		"""List of :py:class:`waflib.Task.Task` ready to be executed by consumers"""

		self.out = Queue(0)
		"""List of :py:class:`waflib.Task.Task` returned by the task consumers"""

		self.count = 0
		"""Amount of tasks that may be processed by :py:class:`waflib.Runner.TaskConsumer`"""

		self.processed = 0
		"""Amount of tasks processed"""

		self.stop = False
		"""Error flag to stop the build"""

		self.error = []
		"""Tasks that could not be executed"""

		self.biter = None
		"""Task iterator which must give groups of parallelizable tasks when calling ``next()``"""

		self.dirty = False
		"""
		Flag that indicates that the build cache must be saved when a task was executed
		(calls :py:meth:`waflib.Build.BuildContext.store`)"""

		self.revdeps = Utils.defaultdict(set)
		"""
		The reverse dependency graph of dependencies obtained from Task.run_after
		"""

		self.spawner = Spawner(self)
		"""
		Coordinating daemon thread that spawns thread consumers
		"""

	def get_next_task(self):
		"""
		Obtains the next Task instance to run

		:rtype: :py:class:`waflib.Task.Task`
		"""
		if not self.outstanding:
			return None
		return self.outstanding.pop()

	def postpone(self, tsk):
		"""
		Adds the task to the list :py:attr:`waflib.Runner.Parallel.postponed`.
		The order is scrambled so as to consume as many tasks in parallel as possible.

		:param tsk: task instance
		:type tsk: :py:class:`waflib.Task.Task`
		"""
		self.postponed.append(tsk)

	def refill_task_list(self):
		"""
		Pulls a next group of tasks to execute in :py:attr:`waflib.Runner.Parallel.outstanding`.
		Ensures that all tasks in the current build group are complete before processing the next one.
		"""
		while self.count > self.numjobs * GAP:
			self.get_out()

		while not self.outstanding:
			if self.count:
				self.get_out()
				if self.outstanding:
					break
			elif self.postponed:
				try:
					cond = self.deadlock == self.processed
				except AttributeError:
					pass
				else:
					if cond:
						lst = []
						for tsk in self.postponed:
							deps = [id(x) for x in tsk.run_after if not x.hasrun]
							lst.append('%s\t-> %r' % (repr(tsk), deps))
							if not deps:
								lst.append('\n  task %r dependencies are done, check its *runnable_status*?' % id(tsk))
						raise Errors.WafError('Deadlock detected: check the task build order%s' % ''.join(lst))
				self.deadlock = self.processed

			if self.postponed:
				self.outstanding.extend(self.postponed)
				self.postponed.clear()
			elif not self.count:
				if self.incomplete:
					for x in self.incomplete:
						for k in x.run_after:
							if not k.hasrun:
								break
						else:
							# dependency added after the build started without updating revdeps
							self.incomplete.remove(x)
							self.outstanding.append(x)
							break
					else:
						raise Errors.WafError('Broken revdeps detected on %r' % self.incomplete)
				else:
					tasks = next(self.biter)
					ready, waiting = self.prio_and_split(tasks)
					self.outstanding.extend(ready)
					self.incomplete.update(waiting)
					self.total = self.bld.total()
					break

	def add_more_tasks(self, tsk):
		"""
		If a task provides :py:attr:`waflib.Task.Task.more_tasks`, then the tasks contained
		in that list are added to the current build and will be processed before the next build group.

		The priorities for dependent tasks are not re-calculated globally

		:param tsk: task instance
		:type tsk: :py:attr:`waflib.Task.Task`
		"""
		if getattr(tsk, 'more_tasks', None):
			more = set(tsk.more_tasks)
			groups_done = set()
			def iteri(a, b):
				for x in a:
					yield x
				for x in b:
					yield x

			# Update the dependency tree
			# this assumes that task.run_after values were updated
			for x in iteri(self.outstanding, self.incomplete):
				for k in x.run_after:
					if isinstance(k, Task.TaskGroup):
						if k not in groups_done:
							groups_done.add(k)
							for j in k.prev & more:
								self.revdeps[j].add(k)
					elif k in more:
						self.revdeps[k].add(x)

			ready, waiting = self.prio_and_split(tsk.more_tasks)
			self.outstanding.extend(ready)
			self.incomplete.update(waiting)
			self.total += len(tsk.more_tasks)

	def mark_finished(self, tsk):
		def try_unfreeze(x):
			# DAG ancestors are likely to be in the incomplete set
			if x in self.incomplete:
				# TODO remove dependencies to free some memory?
				# x.run_after.remove(tsk)
				for k in x.run_after:
					if not k.hasrun:
						break
				else:
					self.incomplete.remove(x)
					self.outstanding.append(x)

		if tsk in self.revdeps:
			for x in self.revdeps[tsk]:
				if isinstance(x, Task.TaskGroup):
					x.prev.remove(tsk)
					if not x.prev:
						for k in x.next:
							# TODO necessary optimization?
							k.run_after.remove(x)
							try_unfreeze(k)
						# TODO necessary optimization?
						x.next = []
				else:
					try_unfreeze(x)
			del self.revdeps[tsk]

	def get_out(self):
		"""
		Waits for a Task that task consumers add to :py:attr:`waflib.Runner.Parallel.out` after execution.
		Adds more Tasks if necessary through :py:attr:`waflib.Runner.Parallel.add_more_tasks`.

		:rtype: :py:attr:`waflib.Task.Task`
		"""
		tsk = self.out.get()
		if not self.stop:
			self.add_more_tasks(tsk)
		self.mark_finished(tsk)

		self.count -= 1
		self.dirty = True
		return tsk

	def add_task(self, tsk):
		"""
		Enqueue a Task to :py:attr:`waflib.Runner.Parallel.ready` so that consumers can run them.

		:param tsk: task instance
		:type tsk: :py:attr:`waflib.Task.Task`
		"""
		self.ready.put(tsk)

	def process_task(self, tsk):
		"""
		Processes a task and attempts to stop the build in case of errors
		"""
		# print("hello wind!!!", tsk.inputs)

		tsk.process()

		# print("-----------------------------!!!", tsk.inputs)

		if tsk.hasrun != Task.SUCCESS:
			self.error_handler(tsk)

	def skip(self, tsk):
		"""
		Mark a task as skipped/up-to-date
		"""
		tsk.hasrun = Task.SKIPPED
		self.mark_finished(tsk)

	def cancel(self, tsk):
		"""
		Mark a task as failed because of unsatisfiable dependencies
		"""
		tsk.hasrun = Task.CANCELED
		self.mark_finished(tsk)

	def error_handler(self, tsk):
		"""
		Called when a task cannot be executed. The flag :py:attr:`waflib.Runner.Parallel.stop` is set,
		unless the build is executed with::

			$ waf build -k

		:param tsk: task instance
		:type tsk: :py:attr:`waflib.Task.Task`
		"""
		if not self.bld.keep:
			self.stop = True
		self.error.append(tsk)

	def task_status(self, tsk):
		"""
		Obtains the task status to decide whether to run it immediately or not.

		:return: the exit status, for example :py:attr:`waflib.Task.ASK_LATER`
		:rtype: integer
		"""
		try:
			return tsk.runnable_status()
		except Exception:
			self.processed += 1
			tsk.err_msg = traceback.format_exc()
			if not self.stop and self.bld.keep:
				self.skip(tsk)
				if self.bld.keep == 1:
					# if -k stop on the first exception, if -kk try to go as far as possible
					if Logs.verbose > 1 or not self.error:
						self.error.append(tsk)
					self.stop = True
				else:
					if Logs.verbose > 1:
						self.error.append(tsk)
				return Task.EXCEPTION

			tsk.hasrun = Task.EXCEPTION
			self.error_handler(tsk)

			return Task.EXCEPTION

	def start(self):
		"""
		Obtains Task instances from the BuildContext instance and adds the ones that need to be executed to
		:py:class:`waflib.Runner.Parallel.ready` so that the :py:class:`waflib.Runner.Spawner` consumer thread
		has them executed. Obtains the executed Tasks back from :py:class:`waflib.Runner.Parallel.out`
		and marks the build as failed by setting the ``stop`` flag.
		If only one job is used, then executes the tasks one by one, without consumers.
		"""
		self.total = self.bld.total()

		while not self.stop:

			self.refill_task_list()

			# consider the next task
			tsk = self.get_next_task()
			if not tsk:
				if self.count:
					# tasks may add new ones after they are run
					continue
				else:
					# no tasks to run, no tasks running, time to exit
					break

			if tsk.hasrun:
				# if the task is marked as "run", just skip it
				self.processed += 1
				continue

			if self.stop: # stop immediately after a failure is detected
				break

			st = self.task_status(tsk)
			if st == Task.RUN_ME:
				self.count += 1
				self.processed += 1

				if self.numjobs == 1:
					tsk.log_display(tsk.generator.bld)
					try:
						self.process_task(tsk)
					finally:
						self.out.put(tsk)
				else:
					self.add_task(tsk)
			elif st == Task.ASK_LATER:
				self.postpone(tsk)
			elif st == Task.SKIP_ME:
				self.processed += 1
				self.skip(tsk)
				self.add_more_tasks(tsk)
			elif st == Task.CANCEL_ME:
				# A dependency problem has occurred, and the
				# build is most likely run with `waf -k`
				if Logs.verbose > 1:
					self.error.append(tsk)
				self.processed += 1
				self.cancel(tsk)

		# self.count represents the tasks that have been made available to the consumer threads
		# collect all the tasks after an error else the message may be incomplete
		while self.error and self.count:
			self.get_out()

		self.ready.put(None)
		if not self.stop:
			assert not self.count
			assert not self.postponed
			assert not self.incomplete

	def prio_and_split(self, tasks):
		"""
		Label input tasks with priority values, and return a pair containing
		the tasks that are ready to run and the tasks that are necessarily
		waiting for other tasks to complete.

		The priority system is really meant as an optional layer for optimization:
		dependency cycles are found quickly, and builds should be more efficient.
		A high priority number means that a task is processed first.

		This method can be overridden to disable the priority system::

			def prio_and_split(self, tasks):
				return tasks, []

		:return: A pair of task lists
		:rtype: tuple
		"""
		# to disable:
		#return tasks, []
		for x in tasks:
			x.visited = 0

		reverse = self.revdeps

		groups_done = set()
		for x in tasks:
			for k in x.run_after:
				if isinstance(k, Task.TaskGroup):
					if k not in groups_done:
						groups_done.add(k)
						for j in k.prev:
							reverse[j].add(k)
				else:
					reverse[k].add(x)

		# the priority number is not the tree depth
		def visit(n):
			if isinstance(n, Task.TaskGroup):
				return sum(visit(k) for k in n.next)

			if n.visited == 0:
				n.visited = 1

				if n in reverse:
					rev = reverse[n]
					n.prio_order = n.tree_weight + len(rev) + sum(visit(k) for k in rev)
				else:
					n.prio_order = n.tree_weight

				n.visited = 2
			elif n.visited == 1:
				raise Errors.WafError('Dependency cycle found!')
			return n.prio_order

		for x in tasks:
			if x.visited != 0:
				# must visit all to detect cycles
				continue
			try:
				visit(x)
			except Errors.WafError:
				self.debug_cycles(tasks, reverse)

		ready = []
		waiting = []
		for x in tasks:
			for k in x.run_after:
				if not k.hasrun:
					waiting.append(x)
					break
			else:
				ready.append(x)
		return (ready, waiting)

	def debug_cycles(self, tasks, reverse):
		tmp = {}
		for x in tasks:
			tmp[x] = 0

		def visit(n, acc):
			if isinstance(n, Task.TaskGroup):
				for k in n.next:
					visit(k, acc)
				return
			if tmp[n] == 0:
				tmp[n] = 1
				for k in reverse.get(n, []):
					visit(k, [n] + acc)
				tmp[n] = 2
			elif tmp[n] == 1:
				lst = []
				for tsk in acc:
					lst.append(repr(tsk))
					if tsk is n:
						# exclude prior nodes, we want the minimum cycle
						break
				raise Errors.WafError('Task dependency cycle in "run_after" constraints: %s' % ''.join(lst))
		for x in tasks:
			visit(x, [])

