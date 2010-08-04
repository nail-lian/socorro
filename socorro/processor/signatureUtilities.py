import re

#===============================================================================
class SignatureUtilities (object):
    _config_requirements = ("irrelevantSignatureRegEx",
                            "prefixSignatureRegEx",
                            "signaturesWithLineNumbersRegEx",
                            #"logger"
                           )
    #---------------------------------------------------------------------------
    def __init__(self, context):
        for x in SignatureUtilities._config_requirements:
            assert x in context, '%s missing from configuration' % x
        self.config = context
        self.irrelevantSignatureRegEx = \
             re.compile(self.config.irrelevantSignatureRegEx)
        self.prefixSignatureRegEx =  \
            re.compile(self.config.prefixSignatureRegEx)
        self.signaturesWithLineNumbersRegEx = \
            re.compile(self.config.signaturesWithLineNumbersRegEx)
        self.fixupSpace = re.compile(r' (?=[\*&,])')
        self.fixupComma = re.compile(r',(?! )')
        self.fixupInteger = re.compile(r'(<|, )(\d+)([uUlL]?)([^\w])')

    #---------------------------------------------------------------------------
    def normalize_signature(self, module_name, function, source, source_line,
                            instruction):
        """ returns a structured conglomeration of the input parameters to serve
        as a signature
        """
        #if function is not None:
        if function:
            if self.signaturesWithLineNumbersRegEx.match(function):
                function = "%s:%s" % (function, source_line)
            # Remove spaces before all stars, ampersands, and commas
            function = self.fixupSpace.sub('',function)
            # Ensure a space after commas
            function = self.fixupComma.sub(', ', function)
            # normalize template signatures with manifest const integers to
            #'int': Bug 481445
            function = self.fixupInteger.sub(r'\1int\4', function)
            return function
        #if source is not None and source_line is not None:
        if source and source_line:
            filename = source.rstrip('/\\')
            if '\\' in filename:
                source = filename.rsplit('\\')[-1]
            else:
                source = filename.rsplit('/')[-1]
            return '%s#%s' % (source, source_line)
        if not module_name:
            module_name = '' # might have been None
        return '%s@%s' % (module_name, instruction)

    #---------------------------------------------------------------------------
    def generateSignatureFromList(self, signatureList, isHang=False, maxLen=255):
        """
        each element of signatureList names a frame in the crash stack; and is:
          - a prefix of a relevant frame: Append this element to the signature
          - a relevant frame: Append this element and stop looking
          - irrelevant: Append this element only after seeing a prefix frame
        The signature is a ' | ' separated string of frame names
        """
        #self.config.logger.debug('generateSignatureFromList %s', str(signatureList))
        # shorten signatureList to the first signatureSentinel
        sentinelLocations = []
        for aSentinel in self.config.signatureSentinels:
            if type(aSentinel) == tuple:
                aSentinel, conditionFn = aSentinel
                if not conditionFn(signatureList):
                    continue
            try:
                sentinelLocations.append(signatureList.index(aSentinel))
            except ValueError:
                pass
        if sentinelLocations:
            signatureList = signatureList[min(sentinelLocations):]
        newSignatureList = []
        prefixFound = False
        for aSignature in signatureList:
            if self.irrelevantSignatureRegEx.match(aSignature):
                if prefixFound:
                    newSignatureList.append(aSignature)
                continue
            newSignatureList.append(aSignature)
            if not self.prefixSignatureRegEx.match(aSignature):
                break
            prefixFound = True
        signature = ' | '.join(newSignatureList)
        if len(signature) > maxLen:
            signature = "%s..." % signature[:maxLen - 3]
        if isHang:
            return "hang | %s" % signature
        return signature