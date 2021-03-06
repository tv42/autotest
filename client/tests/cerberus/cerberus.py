import os, shutil, glob, logging
from autotest_lib.client.bin import test, utils
from autotest_lib.client.common_lib import error

class cerberus(test.test):
    """
    This autotest module runs CTCS2 (Cerberus Test Control System 2), which
    intents to revive the original CTCS project.

    The original test suite (Cerberus Test Control System) was developed for
    the now extinct VA Linux's manufacturing system it has several hardware
    and software stress tests that can be run in parallel. It does have a
    control file system that allows testers to specify the sorts of tests that
    they want to see executed. It's an excelent stress test for hardware and
    kernel.

    @author Manas Kumar Nayak (maknayak@in.ibm.com) (original code)
    @author Lucas Meneghel Rodrigues (lucasmr@br.ibm.com) (rewrite - ctcs)
    @author Cao, Chen (kcao@redhat.com) (use ctcs2 and port it to 64)
    @see: http://sourceforge.net/projects/ctcs2
    @see: http://sourceforge.net/projects/va-ctcs
    """

    version = 2
    def initialize(self):
        """
        Sets the overall failure counter for the test.
        """
        self.nfail = 0


    def setup(self, tarball='ctcs2.tar.bz2', length='4h', tc_opt='-k',
              tcf_contents=None):
        """
        Builds the test suite, and sets up the control file that is going to
        be processed by the ctcs2 engine.
        @param tarball: CTCS2 tarball
        @param length: The amount of time we'll run the test suite
        @param tcf_contents: If the user wants to specify the contents of
                the CTCS2 control file, he could do so trough this parameter. If
                this parameter is provided, length is ignored.
        """
        cerberus2_tarball = utils.unmap_url(self.bindir, tarball, self.tmpdir)
        utils.extract_tarball_to_dir(cerberus2_tarball, self.srcdir)

        os.chdir(self.srcdir)
        # Apply patch to fix build problems on newer distros (absence of
        # asm/page.h include, and platform(32/64bit) related issues.
        p1 = 'patch -p1 < ../0001-Fix-CTCS2-Build.patch'
        utils.system(p1)

        if utils.get_cpu_arch() == 'x86_64':
            p2 = 'patch -p1 < ../0002-Fix-CTCS2-build-in-64-bit-boxes.patch'
            utils.system(p2)

        utils.make()

        # Here we define the cerberus suite control file that will be used.
        # It will be kept on the debug directory for further analysis.
        self.tcf_path = os.path.join(self.debugdir, 'autotest.tcf')

        if not tcf_contents:
            logging.info('Generating cerberus control file')
            # Note about the control file generation command - we are creating
            # a control file with the default tests, except for the kernel
            # compilation test (flag -k).
            g_cmd = './newburn-generator %s %s> %s' % \
                                            (tc_opt, length, self.tcf_path)
            utils.system(g_cmd)
        else:
            logging.debug('TCF file contents supplied, ignoring test length'
                          ' altogether')
            tcf = open(self.tcf_path, 'w')
            tcf.write(tcf_contents)

        logging.debug('Contents of the control file that will be passed to'
                      ' CTCS 2:')
        tcf = open(self.tcf_path, 'r')
        buf = tcf.read()
        logging.debug(buf)


    def run_once(self):
        """
        Runs the test, with the appropriate control file.
        """
        os.chdir(self.srcdir)
        try:
            utils.system('./run %s' % self.tcf_path)
        except:
            self.nfail += 1
        # After we are done with this iterations, we move the log files to
        # the results dir
        log_base_path = os.path.join(self.srcdir, 'log')
        log_dir = glob.glob(os.path.join(log_base_path,
                                         'autotest.tcf.log.*'))[0]
        logging.debug('Copying %s log directory to results dir', log_dir)
        dst = os.path.join(self.resultsdir, os.path.basename(log_dir))
        shutil.move(log_dir, dst)


    def cleanup(self):
        """
        Cleans up source directory and raises on failure.
        """
        if os.path.isdir(self.srcdir):
            shutil.rmtree(self.srcdir)
        if self.nfail != 0:
            raise error.TestFail('Cerberus test suite failed.')
