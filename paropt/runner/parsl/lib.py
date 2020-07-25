from parsl.app.app import python_app

@python_app
def timeCommand(runConfig, **kwargs):
    """Time the main command script. Exits early on failure at any step (setup, main, finish)
    with timeout

    Parameters
    ----------
    runConfig : RunConfig
        config for running the script

    **kwargs : dict
        dictionary that contains parameters for objective function
    
    Returns
    -------
    result : dict
        Contains 'returncode', 'stdout', 'obj_parameters', and 'obj_output' to indicate the result of the run
        If returncode is not 0, obj_output must be ignored.
        obj_output: the result of objective function, which is the final result to optimize to minimum
        obj_parameter: store the parameters used to calculate obj_output. which could be helpful afterwards.
    """
    import os
    import subprocess
    import time
    import sys

    if 'timeout' in kwargs:
        timeout = kwargs['timeout']
    else:
        timeout = sys.maxsize
    def timeScript(script_name, script_content):
        """Helper for writing and running a script"""
        script_path = '{}_{}'.format(script_name, time.time())
        with open(script_path, 'w') as f:
            f.write(script_content)

        timeout_returncode = 0
        obj_parameters = {'running_time': timeout}
        try:
            start_time = time.time()
            proc = subprocess.Popen(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            timeout_returncode = proc.wait(timeout=timeout)
            outs, errs = proc.communicate()
            total_time = time.time() - start_time
            obj_parameters = {'running_time': total_time}

            return {'returncode': proc.returncode, 'stdout': outs.decode(), 'obj_output': total_time, 'obj_parameters': obj_parameters}
        except subprocess.TimeoutExpired:
            return {'returncode': timeout_returncode, 'stdout': f'Timeout', 'obj_output': timeout, 'obj_parameters': obj_parameters} # run time = -1 means timeout


    try:
        # run setup script
        if runConfig.setup_script_content != None:
            res = timeScript('setupScript', runConfig.setup_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
                res['obj_output'] = 0
                res['obj_parameters'] = {}
                return res

        res = timeScript('mainScript', runConfig.command_script_content)

        # if res['stdout'] == 'Timeout':
        #     return res

        # make neg b/c our optimizer is maximizing
        # divide by number of seconds in day to scale down for bayes opt
        res['obj_output'] = -float(res['obj_output']) / 86400
        main_res = res
        if main_res['returncode'] != 0:
            res['stdout'] = f'Failed to run main script: \n{main_res["stdout"]}'
            return main_res

        # run post script
        if runConfig.finish_script_content != None:
            res = timeScript('finishScript', runConfig.finish_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run finish script: \n{res["stdout"]}'
                res['obj_output'] = main_res['obj_output']
                res['obj_parameters'] = main_res['obj_parameters']
                return res
        
        # return the timing result
        return main_res
    except Exception as e:
        # this should not be reached - Indicates a bug in code
        return {'returncode': -1,
                'stdout': "(BUG) Exception occurred during execution: {}".format(e),
                'obj_output': 0}



@python_app
def searchMatrix(runConfig, **kwargs):
    """Find the optimal on a matrix. The script to run need only print the value in the matrix at some point

    Parameters
    ----------
    runConfig : RunConfig
        config for running the script

    **kwargs : dict
        dictionary that contains parameters for objective function
    
    Returns
    -------
    result : dict
        Contains 'returncode', 'stdout', 'obj_parameters', and 'obj_output' to indicate the result of the run
        If returncode is not 0, obj_output must be ignored.
        obj_output: the result of objective function, which is the final result to optimize to minimum
        obj_parameter: store the parameters used to calculate obj_output. which could be helpful afterwards.
    """
    import os
    import subprocess
    import time

    def runScript(script_name, script_content):
        """Helper for writing and running a script"""
        script_path = '{}_{}'.format(script_name, time.time())
        with open(script_path, 'w') as f:
            f.write(script_content)
        # start_time = time.time()
        proc = subprocess.Popen(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outs, errs = proc.communicate()
        # total_time = time.time() - start_time
        res = float(outs.decode('utf-8'))
        obj_parameters = {'running_time': res}
        return {'returncode': proc.returncode, 'stdout': outs.decode(), 'obj_output': res, 'obj_parameters': obj_parameters}

    try:
        # run setup script
        if runConfig.setup_script_content != None:
            res = runScript('setupScript', runConfig.setup_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
                res['obj_output'] = 0
                res['obj_parameters'] = {}
                return res
        
        # time command script
        res = runScript('mainScript', runConfig.command_script_content)
        # make neg b/c our optimizer is maximizing
        # divide by number of seconds in day to scale down for bayes opt
        res['obj_output'] = -res['obj_output']
        main_res = res
        if main_res['returncode'] != 0:
            res['stdout'] = f'Failed to run main script: \n{main_res["stdout"]}'
            return main_res

        # run post script
        if runConfig.finish_script_content != None:
            res = runScript('finishScript', runConfig.finish_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run finish script: \n{res["stdout"]}'
                res['obj_output'] = main_res['obj_output']
                res['obj_parameters'] = main_res['obj_parameters']
                return res
        
        # return the timing result
        return main_res
    except Exception as e:
        # this should not be reached - Indicates a bug in code
        return {'returncode': -1,
                'stdout': "(BUG) Exception occurred during execution: {}".format(e),
                'obj_output': 0}


@python_app
def variantCallerAccu(runConfig, **kwargs):
    """Calculate the accuracy of variant caller. The scripts need to print caller_time, precision, and recall in order (setup, main, finish)
    with timeout

    Parameters
    ----------
    runConfig : RunConfig
        config for running the script

    **kwargs : dict
        dictionary that contains parameters for objective function
    
    Returns
    -------
    result : dict
        Contains 'returncode', 'stdout', 'obj_parameters', and 'obj_output' to indicate the result of the run
        If returncode is not 0, obj_output must be ignored.
        obj_output: the result of objective function, which is the final result to optimize to minimum
        obj_parameter: store the parameters used to calculate obj_output. which could be helpful afterwards.
    """
    import os
    import subprocess
    import time
    import sys
    import math

    if 'timeout' in kwargs and kwargs['timeout'] != 0:
        timeout = kwargs['timeout']
    else:
        timeout = sys.maxsize

    if 'objective' in kwargs:
        obj_func = kwargs['objective']
    else:
        obj_func = 'f1'

    def sigmoid(x):
        return 1/(1+math.exp(-x))
    def func(accu, time):
        return sigmoid(accu/(1-accu)/time)

    def objective(time, accu):
        # change time to half an hour
        time = time/60/30
        return sigmoid(accu/(1-accu)/time)

    def f1_obj(precision, recall):
        if precision + recall == 0:
            return 0
        return 2*precision*recall/(precision+recall)

    def timeScript(script_name, script_content):
        """Helper for writing and running a script"""
        script_path = '{}_{}'.format(script_name, time.time())
        with open(script_path, 'w') as f:
            f.write(script_content)

        timeout_returncode = 0
        obj_parameters = {'running_time': timeout}
        ret_dic = {'returncode': None, 'stdout': None, 'obj_output': None, 'obj_parameters': None}
        try:
            start_time = time.time()
            proc = subprocess.Popen(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            timeout_returncode = proc.wait(timeout=timeout)
            outs, errs = proc.communicate()
            total_time = time.time() - start_time
            
            ret_dic['returncode'] = proc.returncode
            # ret_dic['obj_output'] = total_time
            ret_dic['stdout'] = outs.decode('utf-8')

            # caller time here in sec
            str_res = outs.decode('utf-8')
            res = str_res.strip().split()
            obj_parameters = {'running_time': total_time, 'precision': float(res[-2]), 'recall': float(res[-1]), 'caller_time': float(res[-3])/1000}
            
            # the output of utility, which is used by optimizer
            if obj_func == 'objective':
                obj_output = objective(obj_parameters['caller_time'], f1_obj(obj_parameters['precision'], obj_parameters['recall']))
            elif obj_func == 'f1':
                obj_output = f1_obj(obj_parameters['precision'], obj_parameters['recall'])

            ret_dic['obj_parameters'] = obj_parameters
            ret_dic['obj_output'] = obj_output
            
            return ret_dic
        except subprocess.TimeoutExpired:
            obj_parameters = {'running_time': timeout, 'precision': 0, 'recall': 0, 'caller_time': timeout}
            if obj_func == 'objective':
                obj_output = objective(obj_parameters['caller_time'], f1_obj(obj_parameters['precision'], obj_parameters['recall']))
            elif obj_func == 'f1':
                obj_output = f1_obj(obj_parameters['precision'], obj_parameters['recall'])

            ret_dic['obj_output'] = obj_output
            ret_dic['obj_parameters'] = obj_parameters
            ret_dic['returncode'] = timeout_returncode
            return ret_dic
        except:
            return ret_dic


    try:
        # run setup script
        if runConfig.setup_script_content != None:
            res = timeScript('setupScript', runConfig.setup_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
                res['obj_output'] = 0
                res['obj_parameters'] = {}
                return res

        res = timeScript('mainScript', runConfig.command_script_content)
        if res['stdout'] == 'Timeout':
            return res
        # make neg b/c our optimizer is maximizing
        # divide by number of seconds in day to scale down for bayes opt
        # res['obj_output'] = -res['obj_output'] / 86400
        main_res = res
        if main_res['returncode'] != 0:
            res['stdout'] = f'Failed to run main script: \n{main_res["stdout"]}'
            return main_res

        # run post script
        if runConfig.finish_script_content != None:
            res = timeScript('finishScript', runConfig.finish_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run finish script: \n{res["stdout"]}'
                res['obj_output'] = main_res['obj_output']
                res['obj_parameters'] = main_res['obj_parameters']
                return res
        
        # return the timing result
        return main_res
    except Exception as e:
        # this should not be reached - Indicates a bug in code
        return res
        # return {'returncode': -1,
        #         'stdout': "(BUG) Exception occurred during execution: {}".format(e),
        #         'obj_output': 0}
                

@python_app
def constrainedObjective(runConfig, **kwargs):
    """variantCallerAccu with constrained running time

    Parameters
    ----------
    runConfig : RunConfig
        config for running the script

    **kwargs : dict
        dictionary that contains parameters for objective function
    
    Returns
    -------
    result : dict
        Contains 'returncode', 'stdout', 'obj_parameters', and 'obj_output' to indicate the result of the run
        If returncode is not 0, obj_output must be ignored.
        obj_output: the result of objective function, which is the final result to optimize to minimum
        obj_parameter: store the parameters used to calculate obj_output. which could be helpful afterwards.
    """
    import os
    import subprocess
    import time
    import sys
    import math

    if 'timeout' in kwargs and kwargs['timeout'] != 0:
        timeout = kwargs['timeout']
    else:
        timeout = sys.maxsize
    
    if 'objective' in kwargs:
        obj_func = kwargs['objective']
    else:
        obj_func = 'default'
    if 'boundary' in kwargs:
        boundary = kwargs['boundary']
        if obj_func == 'default':
            obj_func = 'sigmoid_boundary'
    

    def sigmoid(x):
        return 1/(1+math.exp(-x))
    def func(accu, time):
        return sigmoid(accu/(1-accu)/time)

    def objective(time, accu):
        # change time to half an hour
        time = time/60/30
        return sigmoid(accu/(1-accu)/time)

    def f1_cal(precision, recall):
        if precision + recall == 0:
            return 0
        return 2*precision*recall/(precision+recall)


    def sigmoid_boundary(time, f1):
        # change time to hour unit
        time = time / 60 / 60
        return f1 + (-min(0, boundary - time)**2-min(0, boundary - time)) * (f1/abs(boundary - time))
        if precision + recall == 0:
            return 0
        return 2*precision*recall/(precision+recall)

    def default(time, f1):
        return f1
        # time = time / 60 / 60
        # if precision + recall == 0:
        #     return 0
        # return 2*precision*recall/(precision+recall)

    def timeScript(script_name, script_content):
        """Helper for writing and running a script"""
        script_path = '{}_{}'.format(script_name, time.time())
        with open(script_path, 'w') as f:
            f.write(script_content)

        timeout_returncode = 0
        obj_parameters = {'running_time': timeout}
        ret_dic = {'returncode': None, 'stdout': None, 'obj_output': None, 'obj_parameters': None}
        try:
            start_time = time.time()
            proc = subprocess.Popen(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            timeout_returncode = proc.wait(timeout=timeout)
            outs, errs = proc.communicate()
            total_time = time.time() - start_time
            
            ret_dic['returncode'] = proc.returncode
            # ret_dic['obj_output'] = total_time
            ret_dic['stdout'] = outs.decode('utf-8')

            # caller time here in sec
            str_res = outs.decode('utf-8')
            res = str_res.strip().split()
            obj_parameters = {'running_time': total_time, 'precision': float(res[-2]), 'recall': float(res[-1]), 'caller_time': float(res[-3])/1000}
            
            # the output of utility, which is used by optimizer
            if obj_func == 'objective':
                obj_output = objective(obj_parameters['caller_time'], f1_obj(obj_parameters['precision'], obj_parameters['recall']))
            elif obj_func == 'default':
                obj_output = default(obj_parameters['running_time'], f1_cal(obj_parameters['precision'], obj_parameters['recall']))
            elif obj_func == 'sigmoid_boundary':
                obj_output = sigmoid_boundary(obj_parameters['running_time'], f1_cal(obj_parameters['precision'], obj_parameters['recall']))

            ret_dic['obj_parameters'] = obj_parameters
            ret_dic['obj_output'] = obj_output
            
            return ret_dic
        except subprocess.TimeoutExpired:
            obj_parameters = {'running_time': timeout, 'precision': 0, 'recall': 0, 'caller_time': timeout}
            if obj_func == 'objective':
                obj_output = objective(obj_parameters['caller_time'], f1_obj(obj_parameters['precision'], obj_parameters['recall']))
            elif obj_func == 'default':
                obj_output = default(obj_parameters['running_time'], f1_cal(obj_parameters['precision'], obj_parameters['recall']))
            elif obj_func == 'sigmoid_boundary':
                obj_output = sigmoid_boundary(obj_parameters['running_time'], f1_cal(obj_parameters['precision'], obj_parameters['recall']))

            ret_dic['obj_output'] = obj_output
            ret_dic['obj_parameters'] = obj_parameters
            ret_dic['returncode'] = timeout_returncode
            return ret_dic
        except:
            return ret_dic


    try:
        # run setup script
        if runConfig.setup_script_content != None:
            res = timeScript('setupScript', runConfig.setup_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
                res['obj_output'] = 0
                res['obj_parameters'] = {}
                return res

        res = timeScript('mainScript', runConfig.command_script_content)
        if res['stdout'] == 'Timeout':
            return res
        # make neg b/c our optimizer is maximizing
        # divide by number of seconds in day to scale down for bayes opt
        # res['obj_output'] = -res['obj_output'] / 86400
        main_res = res
        if main_res['returncode'] != 0:
            res['stdout'] = f'Failed to run main script: \n{main_res["stdout"]}'
            return main_res

        # run post script
        if runConfig.finish_script_content != None:
            res = timeScript('finishScript', runConfig.finish_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run finish script: \n{res["stdout"]}'
                res['obj_output'] = main_res['obj_output']
                res['obj_parameters'] = main_res['obj_parameters']
                return res
        
        # return the timing result
        return main_res
    except Exception as e:
        # this should not be reached - Indicates a bug in code
        return res
        # return {'returncode': -1,
        #         'stdout': "(BUG) Exception occurred during execution: {}".format(e),
        #         'obj_output': 0}




@python_app
def localConstrainedObjective(runConfig, **kwargs):
    """variantCallerAccu with constrained running time

    Parameters
    ----------
    runConfig : RunConfig
        config for running the script

    **kwargs : dict
        dictionary that contains parameters for objective function
    
    Returns
    -------
    result : dict
        Contains 'returncode', 'stdout', 'obj_parameters', and 'obj_output' to indicate the result of the run
        If returncode is not 0, obj_output must be ignored.
        obj_output: the result of objective function, which is the final result to optimize to minimum
        obj_parameter: store the parameters used to calculate obj_output. which could be helpful afterwards.
    """
    import os
    import subprocess
    import time
    import sys
    import math

    if 'timeout' in kwargs and kwargs['timeout'] != 0:
        timeout = kwargs['timeout']
    else:
        timeout = sys.maxsize
    
    if 'objective' in kwargs:
        obj_func = kwargs['objective']
    else:
        obj_func = 'default'
    
    if 'time_boundary' not in kwargs.keys():
        time_boundary = 24
    else:
        time_boundary = kwargs['time_boundary']


    baseline_time = None
    sensitivity = 2
    if obj_func == 'objective':
        pass
    elif obj_func == 'default':
        pass
    elif obj_func == 'sigmoid_boundary':
        f1_boundary = kwargs['f1_boundary']
        sigmoid_coef = kwargs['sigmoid_coef']
    elif obj_func == 'neg_boundary':
        f1_boundary = kwargs['f1_boundary']
        pass
    elif obj_func == 'frac_boundary':
        f1_boundary = kwargs['f1_boundary']
        pass
    elif obj_func == 'linear_boundary':
        f1_boundary = kwargs['f1_boundary']
    elif obj_func == 'frac_linear_boundary':
        f1_boundary = kwargs['f1_boundary']
    elif obj_func == 'new_sigmoid':
        f1_boundary = kwargs['f1_boundary']
        alpha = kwargs['alpha']
        if 'sensitivity' in kwargs.keys():
            sensitivity = kwargs['sensitivity']
        if 'baseline_time' in kwargs.keys():
            baseline_time = kwargs['baseline_time'] / 60
    elif obj_func == 'new_linear':
        f1_boundary = kwargs['f1_boundary']
        alpha = kwargs['alpha']
        if 'sensitivity' in kwargs.keys():
            sensitivity = kwargs['sensitivity']
        if 'baseline_time' in kwargs.keys():
            baseline_time = kwargs['baseline_time'] / 60

    def sigmoid(x):
        return 1/(1+math.exp(-x))
    def func(accu, time):
        return sigmoid(accu/(1-accu)/time)

    def objective(time, accu):
        # change time to half an hour
        time = time/60/30
        return sigmoid(accu/(1-accu)/time)

    def f1_cal(precision, recall):
        if precision + recall == 0:
            return 0
        return 2*precision*recall/(precision+recall)


    def new_sigmoid(time, f1):
        time = time/60
        return 1
        if f1 < f1_boundary:
            return 0
        if not baseline_time:
            return 0
        return 0.24/sensitivity/alpha * (f1 - f1_boundary) - sigmoid(time/(sensitivity*baseline_time)) + 1

    def new_linear(time, f1):
        time = time/60
        if f1 < f1_boundary:
            return 0
        return 1/alpha/(baseline_time*sensitivity) * (f1 - f1_boundary) - (1/(sensitivity*baseline_time) * time) + boundary

    def sigmoid_boundary(time, f1):
        time = time/60
        if f1 < f1_boundary:
            return 0
        return f1 - sigmoid((time - time_boundary)/sigmoid_coef)*f1_boundary


    def neg_boundary(time, f1):
        time = time / 60
        if f1 < f1_boundary:
            return 0
        return f1 - time

    def frac_boundary(time, f1):
        time = time / 60
        if f1 < f1_boundary:
            return 0
        return f1 / time

    def linear_boundary(time, f1):
        time = time / 60
        if f1 < f1_boundary:
            return 0
        return f1 + (time_boundary - time) / time_boundary * f1_boundary

    def frac_linear_boundary(time, f1):
        time = time / 60
        if f1 < f1_boundary:
            return 0
        return f1 + f1 / time + (time_boundary - time) / time_boundary * f1_boundary


    def default(time, f1):
        return f1
        time = time / 60 / 60
        if precision + recall == 0:
            return 0
        return 2*precision*recall/(precision+recall)

    def timeScript(script_name, script_content):
        """Helper for writing and running a script"""
        script_path = '{}_{}'.format(script_name, time.time())
        with open(script_path, 'w') as f:
            f.write(script_content)

        timeout_returncode = 0
        obj_parameters = {'running_time': timeout}
        ret_dic = {'returncode': None, 'stdout': None, 'obj_output': None, 'obj_parameters': None}
        try:
            start_time = time.time()
            proc = subprocess.Popen(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            timeout_returncode = proc.wait(timeout=timeout)
            outs, errs = proc.communicate()
            total_time = time.time() - start_time
            
            ret_dic['returncode'] = proc.returncode
            # ret_dic['obj_output'] = total_time
            ret_dic['stdout'] = outs.decode('utf-8')

            # caller time here in sec
            str_res = outs.decode('utf-8')
            res = str_res.strip().split()
            # obj_parameters = {'running_time': float(res[-1]), 'precision': float(res[-3]), 'recall': float(res[-2]), 'caller_time': float(res[-1])}
            obj_parameters = {'running_time': float(res[-1]), 'f1': float(res[-2]), 'caller_time': float(res[-1])}
            
            # the output of utility, which is used by optimizer
            if obj_func == 'objective':
                # obj_output = objective(obj_parameters['caller_time'], f1_obj(obj_parameters['precision'], obj_parameters['recall']))
                obj_output = objective(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'default':
                obj_output = default(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'sigmoid_boundary':
                obj_output = sigmoid_boundary(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'neg_boundary':
                obj_output = neg_boundary(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'frac_boundary':
                obj_output = frac_boundary(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'linear_boundary':
                obj_output = linear_boundary(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'frac_linear_boundary':
                obj_output = frac_linear_boundary(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'new_sigmoid':
                ret_dic['obj_output'] = 0
                if 'baseline_time' not in kwargs.keys():
                    baseline_time = obj_parameters['caller_time']
                ret_dic['obj_output'] = 1
                if not alpha:
                    obj_output = 1
                if not sensitivity:
                    obj_output = 2
                ret_dic['obj_output'] = 2
                if not baseline_time:
                    obj_output = 0
                ret_dic['obj_output'] = 3
                # obj_output = new_sigmoid(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'new_linear':
                if baseline_time is None:
                    baseline_time = obj_parameters['caller_time']
                obj_output = new_linear(obj_parameters['caller_time'], obj_parameters['f1'])

            ret_dic['obj_parameters'] = obj_parameters
            ret_dic['obj_output'] = obj_output
            
            return ret_dic
        except subprocess.TimeoutExpired:
            obj_parameters = {'running_time': timeout, 'f1': 0, 'caller_time': timeout}
            if obj_func == 'objective':
                obj_output = objective(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'default':
                obj_output = default(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'sigmoid_boundary':
                obj_output = sigmoid_boundary(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'neg_boundary':
                obj_output = neg_boundary(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'frac_boundary':
                obj_output = frac_boundary(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'linear_boundary':
                obj_output = linear_boundary(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'frac_linear_boundary':
                obj_output = frac_linear_boundary(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'new_sigmoid':
                if baseline_time is None:
                    baseline_time = obj_parameters['caller_time']
                obj_output = new_sigmoid(obj_parameters['caller_time'], obj_parameters['f1'])
            elif obj_func == 'new_linear':
                if baseline_time is None:
                    baseline_time = obj_parameters['caller_time']
                obj_output = new_linear(obj_parameters['caller_time'], obj_parameters['f1'])

            ret_dic['obj_output'] = obj_output
            ret_dic['obj_parameters'] = obj_parameters
            ret_dic['returncode'] = timeout_returncode
            return ret_dic
        except Exception as e:
            ret_dic['errors'] = e
            return ret_dic


    try:
        # run setup script
        if runConfig.setup_script_content != None:
            res = timeScript('setupScript', runConfig.setup_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run setupscript: \n{res["stdout"]}'
                res['obj_output'] = 0
                res['obj_parameters'] = {}
                return res

        res = timeScript('mainScript', runConfig.command_script_content)
        if res['stdout'] == 'Timeout':
            return res
        # make neg b/c our optimizer is maximizing
        # divide by number of seconds in day to scale down for bayes opt
        # res['obj_output'] = -res['obj_output'] / 86400
        main_res = res
        if main_res['returncode'] != 0:
            res['stdout'] = f'Failed to run main script: \n{main_res["stdout"]}'
            return main_res

        # run post script
        if runConfig.finish_script_content != None:
            res = timeScript('finishScript', runConfig.finish_script_content)
            if res['returncode'] != 0:
                res['stdout'] = f'Failed to run finish script: \n{res["stdout"]}'
                res['obj_output'] = main_res['obj_output']
                res['obj_parameters'] = main_res['obj_parameters']
                return res
        
        # return the timing result
        return main_res
    except Exception as e:
        # this should not be reached - Indicates a bug in code
        return res
        # return {'returncode': -1,
        #         'stdout': "(BUG) Exception occurred during execution: {}".format(e),
        #         'obj_output': 0}